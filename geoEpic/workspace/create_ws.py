import os
import shutil
import argparse

def create_workspace(target_dir, template_dir):
    if not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok = True)
        
    # os.chdir(target_dir)
    # Ensure the template directory exists
    if not os.path.exists(template_dir):
        print(f"Error: Template directory '{template_dir}' not found.")
        return
    
    # Copy the content of the template directory to the target directory
    for item in os.listdir(template_dir):
        source_item = os.path.join(template_dir, item)
        target_item = os.path.join(target_dir, item)

        if os.path.isdir(source_item):
            shutil.copytree(source_item, target_item)
        else:
            # if source_item.split('.')[-1] != 'py':
            shutil.copy2(source_item, target_item)

    print(f"Workspace set up at: {target_dir}")

def main():
    parser = argparse.ArgumentParser(description="Create Workspace for EPIC package")
    parser.add_argument('-w', '--working_dir', required=True, help='Working directory where workspace will be created')
    args = parser.parse_args()

    # Assuming your template directory is located at "./ws_template" relative to the script
    script_dir = os.path.dirname(os.path.dirname(__file__))
    template_directory = os.path.join(script_dir, "templates/ws_template")
    
    create_workspace(args.working_dir, template_directory)

if __name__ == '__main__':
    main()
