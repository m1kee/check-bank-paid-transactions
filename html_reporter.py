import os
import datetime
import webbrowser
import pandas as pd
import config
from utils import format_clp

def generate_and_open_html_report(no_match_df: pd.DataFrame, total_unpaid: float, total_payments: float, total_shopping: float, start_date: str = None):
    """
    Generates a minimalist dark-mode HTML report from the analysis data
    and automatically opens it in the default web browser.
    """
    # 1. Create reports directory if it doesn't exist
    reports_folder = getattr(config, "REPORTS_FOLDER", "reports")
    os.makedirs(reports_folder, exist_ok=True)
    
    # 2. Generate a unique filename
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    html_filename = f"report_{timestamp}.html"
    html_filepath = os.path.join(reports_folder, html_filename)
    
    # 3. Format monetary values
    diff = total_payments - total_shopping
    str_total_unpaid = format_clp(total_unpaid)
    str_total_payments = format_clp(total_payments)
    str_total_shopping = format_clp(total_shopping)
    str_diff = format_clp(diff)
    
    # 4. Generate the HTML table rows
    table_rows = ""
    if not no_match_df.empty:
        for _, row in no_match_df.iterrows():
            date_str = row['Date'].strftime('%d/%m/%Y') if pd.notnull(row['Date']) else ""
            desc = row.get('Description', '')
            city = row.get('City', '')
            amount = format_clp(row.get('Amount ($)', 0))
            
            table_rows += f"""
            <tr>
                <td>{date_str}</td>
                <td>{desc}</td>
                <td>{city}</td>
                <td class="amount-cell unpaid-amount">{amount}</td>
            </tr>
            """
    else:
        table_rows = """
        <tr>
            <td colspan="4" class="empty-state">No hay compras de 1 cuota sin pagar. ¡Todo está en orden!</td>
        </tr>
        """
        
    filter_text = f"<p class='subtitle'>Filtrado desde: {start_date}</p>" if start_date else ""

    # 5. HTML Template with modern dark theme
    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reporte de Análisis Bancario</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-color: #121212;
            --card-bg: #1e1e1e;
            --text-main: #f3f4f6;
            --text-secondary: #9ca3af;
            --accent: #3b82f6;
            --danger: #ef4444;
            --success: #10b981;
            --border: #374151;
        }}
        
        body {{
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            margin: 0;
            padding: 40px 20px;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1000px;
            margin: 0 auto;
        }}
        
        header {{
            margin-bottom: 40px;
            text-align: center;
        }}
        
        h1 {{
            font-size: 2.5rem;
            margin: 0 0 10px 0;
            font-weight: 700;
        }}
        
        .subtitle {{
            color: var(--text-secondary);
            font-size: 1.1rem;
            margin: 0;
        }}
        
        /* Dashboard Cards */
        .dashboard {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        
        .card {{
            background-color: var(--card-bg);
            border-radius: 12px;
            padding: 24px;
            border: 1px solid var(--border);
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            transition: transform 0.2s ease;
        }}
        
        .card:hover {{
            transform: translateY(-5px);
        }}
        
        .card h3 {{
            color: var(--text-secondary);
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin: 0 0 10px 0;
            font-weight: 600;
        }}
        
        .card .value {{
            font-size: 1.8rem;
            font-weight: 700;
            margin: 0;
        }}
        
        .value.danger {{ color: var(--danger); }}
        .value.success {{ color: var(--success); }}
        .value.neutral {{ color: var(--text-main); }}
        
        /* Table Styles */
        .table-container {{
            background-color: var(--card-bg);
            border-radius: 12px;
            border: 1px solid var(--border);
            overflow: hidden;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }}
        
        .table-header {{
            padding: 20px 24px;
            border-bottom: 1px solid var(--border);
        }}
        
        .table-header h2 {{
            margin: 0;
            font-size: 1.25rem;
            font-weight: 600;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            text-align: left;
        }}
        
        th, td {{
            padding: 16px 24px;
            border-bottom: 1px solid var(--border);
        }}
        
        th {{
            background-color: rgba(255, 255, 255, 0.02);
            color: var(--text-secondary);
            font-weight: 600;
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        
        tr:last-child td {{
            border-bottom: none;
        }}
        
        tr:hover td {{
            background-color: rgba(255, 255, 255, 0.03);
        }}
        
        .amount-cell {{
            text-align: right;
            font-family: monospace;
            font-size: 1.05rem;
        }}
        
        .unpaid-amount {{
            color: var(--danger);
            font-weight: 600;
        }}
        
        .empty-state {{
            text-align: center;
            padding: 40px !important;
            color: var(--success);
            font-weight: 500;
        }}
        
        .footer {{
            text-align: center;
            margin-top: 40px;
            color: var(--text-secondary);
            font-size: 0.85rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Análisis de Movimientos</h1>
            {filter_text}
            <p class="subtitle">Reporte generado el {datetime.datetime.now().strftime('%d/%m/%Y a las %H:%M')}</p>
        </header>

        <div class="dashboard">
            <div class="card">
                <h3>Total por Pagar (Sin Empate)</h3>
                <p class="value danger">{str_total_unpaid}</p>
            </div>
            <div class="card">
                <h3>Total Pagos Registrados</h3>
                <p class="value success">{str_total_payments}</p>
            </div>
            <div class="card">
                <h3>Total Compras Registradas</h3>
                <p class="value neutral">{str_total_shopping}</p>
            </div>
            <div class="card">
                <h3>Diferencia (Pagos - Compras)</h3>
                <p class="value {'success' if diff >= 0 else 'danger'}">{str_diff}</p>
            </div>
        </div>

        <div class="table-container">
            <div class="table-header">
                <h2>Detalle de Compras No Pagadas</h2>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Fecha</th>
                        <th>Descripción</th>
                        <th>Ciudad</th>
                        <th style="text-align: right;">Monto</th>
                    </tr>
                </thead>
                <tbody>
                    {table_rows}
                </tbody>
            </table>
        </div>
        
        <div class="footer">
            <p>Reporte generado automáticamente por Account Analysis Tool</p>
        </div>
    </div>
</body>
</html>"""

    # 6. Save HTML file
    with open(html_filepath, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    print(f"✅ Reporte HTML generado exitosamente en: {html_filepath}")
    
    # 7. Open in default browser
    try:
        # get absolute path to guarantee it opens correctly
        abs_path = os.path.abspath(html_filepath)
        file_url = f"file:///{abs_path.replace(os.sep, '/')}"
        print("Abriendo reporte en el navegador...")
        webbrowser.open(file_url)
    except Exception as e:
        print(f"No se pudo abrir el navegador automáticamente: {e}")

    return html_filepath
