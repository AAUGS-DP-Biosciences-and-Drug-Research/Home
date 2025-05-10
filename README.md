# graduate-doc-template


This template repository renders the `README.md` file into a styled HTML page and a downloadable PDF using a Jinja2 template and WeasyPrint. It is fully automated via GitHub Actions and designed to be reused across graduate school documentation categories.

## 🚀 Features
- 📄 Write content in Markdown (`README.md`)
- 🎨 Apply custom styling via Jinja2 template
- 🌐 Deploy as a static website via GitHub Pages
- 🧾 Export as PDF using WeasyPrint

## 🛠️ Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/YOUR-ORG/graduate-doc-template.git your-topic-doc
   cd your-topic-doc
   ```

2. Edit `README.md` with your content.
3. Commit and push changes.

GitHub Actions will:
- Convert the README to HTML using the Jinja2 template
- Export the HTML as a PDF
- Publish both to GitHub Pages

## 📄 Output
- `public/index.html` – Web version
- `public/Document.pdf` – Downloadable PDF
