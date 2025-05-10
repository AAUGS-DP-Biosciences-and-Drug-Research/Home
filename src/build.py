import markdown
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
import weasyprint
import sys

try:
    print("📄 Reading README.md...")
    md_path = Path("README.md")
    if not md_path.exists():
        raise FileNotFoundError("README.md not found.")

    md_content = md_path.read_text(encoding="utf-8")
    html_content = markdown.markdown(md_content, extensions=["extra", "tables"])

    print("🎨 Rendering templates...")
    env = Environment(loader=FileSystemLoader("src/templates"))

    # Website HTML
    template_html = env.get_template("template.html")
    rendered_html = template_html.render(content=html_content)

    # PDF HTML
    template_pdf = env.get_template("pdf_template.html")
    rendered_pdf_html = template_pdf.render(content=html_content)

    output_dir = Path("public")
    output_dir.mkdir(exist_ok=True)

    # Save HTML for web
    html_path = output_dir / "index.html"
    html_path.write_text(rendered_html, encoding="utf-8")
    print(f"✅ HTML written to {html_path}")

    # Save PDF
    pdf_path = output_dir / "Document.pdf"
    weasyprint.HTML(string=rendered_pdf_html).write_pdf(pdf_path)
    print(f"✅ PDF written to {pdf_path}")

except Exception as e:
    print(f"❌ Build failed: {e}")
    sys.exit(1)
