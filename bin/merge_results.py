import os
import sys
import glob
from weasyprint import HTML
from jinja2 import Template

def generate_html_report(dataset_plots, output_html):
    """ Generate an interactive HTML report. """
    template_str = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Final Report</title>
        <style>
            body { font-family: Arial, sans-serif; }
            .container { width: 80%; margin: auto; }
            img { max-width: 100%; }
            .dataset { margin-bottom: 20px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Silhouette Score Analysis Report</h1>
            {% for dataset, plot in dataset_plots.items() %}
                <div class="dataset">
                    <h2>{{ dataset }}</h2>
                    <img src="{{ plot }}" alt="Plot for {{ dataset }}">
                </div>
            {% endfor %}
        </div>
    </body>
    </html>
    """
    template = Template(template_str)

    dataset_plot_dict = {os.path.basename(p).replace(".png", ""): p for p in dataset_plots}
    
    with open(output_html, "w") as f:
        f.write(template.render(dataset_plots=dataset_plot_dict))

def generate_pdf_report(html_file, pdf_file):
    """ Convert HTML report to PDF using WeasyPrint. """
    HTML(html_file).write_pdf(pdf_file)

if __name__ == "__main__":
    dataset_plots = glob.glob("*.png")  # Get all dataset plots in the directory
    output_pdf = sys.argv[1]
    output_html = sys.argv[2]

    generate_html_report(dataset_plots, output_html)
    generate_pdf_report(output_html, output_pdf)

    print(f"HTML report saved as {output_html}")
    print(f"PDF report saved as {output_pdf}")

