import os
import numpy as np
import pandas as pd
from tqdm import tqdm
import pygmo as pg

class PygmoProblem:
    """
    A class designed to define an optimization problem for use with the PyGMO library, 
    
    Attributes:
        workspace (Workspace): The workspace object managing the environment in which the model runs.
        dfs (tuple): A tuple of DataFrame-like objects that hold constraints and parameters for the problem.
        bounds (np.ndarray): An array of parameter bounds, each specified as (min, max).
        lens (np.ndarray): An array of cumulative lengths that help in splitting parameters for each DataFrame.
    """

    def __init__(self, workspace, *dfs):
        """
        Initializes the PygmoProblem with a workspace and one or more parameter data frames.

        Args:
            workspace (Workspace): An instance of a Workspace used to run models and evaluate fitness.
            *dfs (DataFrame-like): Variable number of parameter objects with constraints.
        
        Raises:
            Exception: If no fitness function is set in the workspace.
        """
        self.workspace = workspace
        if not hasattr(self.workspace, 'objective_function') or self.workspace.objective_function is None:
            raise Exception("Objective function is not set for the workspace")

        self.dfs = dfs
        cons, lens = [], []
        for df in dfs:
            cons += list(df.constraints())  # Assuming each df has a constraints() method returning tuples (min, max)
            lens.append(len(df.constraints()))
        self.bounds = np.array(cons)
        self.lens = np.cumsum(lens)

    def apply_solution(self, x):
        """
        Apply a solution vector to update parameters in all dataframes.

        Args:
            x (np.array): A solution vector containing parameter values for all data frames.
        """
        # Split the parameters according to self.lens, excluding the last cumulative length
        split_x = np.split(x, self.lens[:-1])
        
        # Update parameters in each dataframe and save
        for df, vals in zip(self.dfs, split_x):
            df.edit(vals)
            if hasattr(df, 'save'):
                df.save(self.workspace.model.path)

    def fitness(self, x):
        """
        Evaluate the fitness of a solution vector 'x'.

        Args:
            x (np.array): A solution vector containing parameter values for all data frames.

        Returns:
            float: The fitness value as determined by the workspace's fitness function.
        """
        self.apply_solution(x)
        return self.workspace.run(progress_bar = False)
    
    @property
    def current(self):
        """
        Retrieve the current parameter values from all data frames.

        Returns:
            np.array: A concatenated array of current parameter values from all data frames.
        """
        return np.concatenate([df.current for df in self.dfs])
    
    @property
    def var_names(self):
        """
        Get the variable names from all data frames.

        Returns:
            list: A list of variable names concatenated from all data frames. Each data frame's 
                 var_names() method is called and the results are combined into a single list.
        """
        names = []
        for df in self.dfs:
            names.extend(df.var_names())
        return names

    def get_bounds(self):
        """
        Get the bounds for parameters as tuples of (min, max) values for each parameter across all data frames.

        Returns:
            tuple: Two numpy arrays representing the lower and upper bounds of the parameters.
        """
        return self.bounds[:, 0], self.bounds[:, 1]


class Problem_Wrapper:
    """
    A wrapper class that provides a simplified interface for optimization and sensitivity analysis.
    
    Attributes:
        problem (PygmoProblem): The PygmoProblem instance.
        pg_problem (pg.problem): The wrapped PyGMO problem instance.
        algorithm: The PyGMO algorithm instance for optimization.
        population: The PyGMO population instance.
        population_size (int): Size of the population for optimization.
    """

    def __init__(self, workspace, *dfs):
        """
        Initialize the calibration problem.

        Args:
            workspace (Workspace): The workspace object managing the environment.
            *dfs (DataFrame-like): Variable number of parameter objects with constraints.
        """
        self.problem = PygmoProblem(workspace, *dfs)
        self.pg_problem = pg.problem(self.problem)
        # Initialize optimization components as None
        self.algorithm = None
        self.pg_algorithm = None
        self.population = None
        self.population_size = None
        self.workspace = workspace

    def init(self, algorithm, **kwargs):
        """
        Initialize the optimization algorithm and population.

        Args:
            algorithm: PyGMO algorithm class (e.g., pg.pso_gen)
            **kwargs: Additional keyword arguments to pass to the algorithm
        """
        # Store the algorithm with gen=1 and any additional kwargs
        self.algorithm = algorithm(gen=1, **kwargs)
        self.pg_algorithm = pg.algorithm(self.algorithm)
        
    def optimize(self, population_size, generations):
        """
        Run the optimization process.
        
        Args:
            population_size (int): Size of the population for optimization
            generations (int): Number of generations to run
            
        Returns:
            The evolved population after optimization
        """
        from collections import deque
        from time import perf_counter
        
        if self.pg_algorithm is None:
            raise Exception("Must call init() before optimize()")
        
        # Print fitness before optimization
        fitness_before = self.workspace.run(progress_bar = False)
        print(f"Fitness before optimization: {fitness_before}")
        print("Setting Initial Population")
        self.population = pg.population(self.pg_problem, size=population_size)

        # Moving average of recent per-gen durations
        recent = deque(maxlen=10)
        print("optimizing...")
        bar = tqdm(total=generations, unit="gen", leave=True)
        for g in range(1, generations + 1):
            t0 = perf_counter()
            self.population = self.pg_algorithm.evolve(self.population)  # one generation
            dt = perf_counter() - t0
            
            recent.append(dt)
            mean_dt = sum(recent) / len(recent)
            eta = (generations - g) * mean_dt
            
            # Show best fitness compactly (first objective if multi-objective)
            f = self.population.champion_f
            f0 = float(f[0] if np.ndim(f) else f)
            bar.set_postfix({"Best_Fitness": f"{f0:.6g}"})
            bar.update(1)
            self.workspace.clear_outputs()
        
        bar.close()
        print(f"Final best fitness: {self.population.champion_f}")


    def sensitivity_analysis(self, base_no_of_samples, method):
        """
        Perform sensitivity analysis using SALib with status updates.

        Parameters:
        - base_no_of_samples (int): Base number of samples to generate.
        - method (str): Sensitivity analysis method ('sobol', 'efast', 'morris').

        Returns:
        - dict: Results of the sensitivity analysis.
        """
        from SALib import ProblemSpec
        
        # Get bounds and variable names from the problem
        lower_bounds, upper_bounds = self.problem.get_bounds()
        var_names = self.problem.var_names
        
        # Create bounds in the format expected by SALib (list of [min, max] pairs)
        bounds = [[lower_bounds[i], upper_bounds[i]] for i in range(len(var_names))]
        
        # Define the problem using ProblemSpec
        sp = ProblemSpec({
            'num_vars': len(bounds),
            'names': var_names,
            'bounds': bounds,
            'outputs': ['Y']
        })

        # Select the sampling method based on the method argument
        if method == 'sobol':
            print(f"Sampling using Sobol with {base_no_of_samples} samples...")
            sp.sample_sobol(base_no_of_samples)
        elif method == 'efast':
            print(f"Sampling using eFAST with {base_no_of_samples} samples...")
            sp.sample_fast(base_no_of_samples)
        elif method == 'morris':
            print(f"Sampling using Morris with {base_no_of_samples} samples...")
            sp.sample_morris(base_no_of_samples)
        else:
            raise ValueError("Unsupported method. Choose from 'sobol', 'efast', or 'morris'.")

        # Function to evaluate model outputs
        def evaluate(samples):
            print("Evaluating objective function for each sample...")
            outputs = []
            for i, sample in enumerate(tqdm(samples)):
                output = self.problem.fitness(sample)
                # Handle multi-objective case
                if hasattr(output, '__len__') and not isinstance(output, str):
                    if len(output) > 1:
                        print('Warning: Multi-objective output detected, choosing the first objective')
                    outputs.append(float(output[0]))
                else:
                    outputs.append(float(output))
            return np.array(outputs)

        # Evaluate samples
        sp.evaluate(evaluate)

        # Perform sensitivity analysis
        print(f"Performing sensitivity analysis using {method}...")
        if method == 'sobol':
            results = sp.analyze_sobol(print_to_console=True)
        elif method == 'efast':
            results = sp.analyze_fast(print_to_console=True)
        elif method == 'morris':
            results = sp.analyze_morris(print_to_console=True)

        print(f"Sensitivity analysis completed.")
        return results
