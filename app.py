from flask import Flask
import os
import struct
import pyodbc
from azure.identity import DefaultAzureCredential

app = Flask(__name__)

SERVER = "sql-webapp-dev-2026.database.windows.net"
DATABASE = "sqldb-webapp-dev"

def get_connection():
    credential = DefaultAzureCredential()
    token = credential.get_token("https://database.windows.net/.default").token

    token_bytes = token.encode("utf-16-le")
    token_struct = struct.pack(f"<I{len(token_bytes)}s", len(token_bytes), token_bytes)

    connection_string = (
        f"Driver={{ODBC Driver 18 for SQL Server}};"
        f"Server=tcp:{SERVER},1433;"
        f"Database={DATABASE};"
        f"Encrypt=yes;"
        f"TrustServerCertificate=no;"
    )

    SQL_COPT_SS_ACCESS_TOKEN = 1256

    return pyodbc.connect(
        connection_string,
        attrs_before={SQL_COPT_SS_ACCESS_TOKEN: token_struct}
    )

@app.route("/")
def home():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT Id, Title, Description, Status, CreatedAt
        FROM CloudTasks
        ORDER BY Id DESC
    """)

    tasks = cursor.fetchall()

    cursor.close()
    conn.close()

    html = """
    <h1>Azure Cloud Portfolio</h1>
    <h2>Cloud Tasks</h2>

    <p>Deployed automatically using GitHub Actions CI/CD.</p>

    <table border="1" cellpadding="8">
        <tr>
            <th>ID</th>
            <th>Title</th>
            <th>Description</th>
            <th>Status</th>
            <th>Created At</th>
        </tr>
    """

    for task in tasks:
        html += f"""
        <tr>
            <td>{task.Id}</td>
            <td>{task.Title}</td>
            <td>{task.Description}</td>
            <td>{task.Status}</td>
            <td>{task.CreatedAt}</td>
        </tr>
        """

    html += "</table>"

    return html

if __name__ == "__main__":
    app.run()