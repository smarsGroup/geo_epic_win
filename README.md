# geo_epic_win
Windows version of geo epic

# pushing docs

This project uses [MkDocs](https://www.mkdocs.org/) with the [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/getting-started/) theme to generate a static site from Markdown files.

## Prerequisites

Before you begin, make sure you have the following installed on your machine:

- Python 3.x
- `pip` (Python package manager)
- `sudo` privileges (if you're using Linux or macOS)

## Installation

### Step 1: Install MkDocs

On Linux or macOS, you can use the following command to install MkDocs:

```bash
sudo apt install mkdocs
```

Alternatively, you can use pip to install MkDocs on any platform:

```bash
pip install mkdocs
```

### Step 2: Install the Material for MkDocs theme
Install the Material theme for MkDocs using pip:

```bash
pip install mkdocs-material
```

### Step 3: Install the pymdown-extensions (Optional)
For additional Markdown extensions supported by the Material theme, install the pymdown-extensions:

```bash
pip install pymdown-extensions
```

Running Locally
To preview your documentation site locally, use the following command:

```bash
mkdocs serve
```
This will start a local development server. You can access the site at http://127.0.0.1:8000 in your browser to view changes in real-time.

### Step 4: Deploying to GitHub Pages
Once you're ready to deploy your MkDocs site to GitHub Pages, use the following command:

```bash
mkdocs gh-deploy --force
```
This will build your site and push it to the gh-pages branch of your GitHub repository, which will automatically serve the site using GitHub Pages.

### Editing Content
To edit the content of your MkDocs site, modify the Markdown files in the docs/ folder. For detailed instructions on editing and configuring your MkDocs project, refer to the official documentation:

[Material for MkDocs - Getting Started](https://squidfunk.github.io/mkdocs-material/getting-started/) 
