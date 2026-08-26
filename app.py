from flask import Flask, request, redirect, url_for
import struct
import pyodbc
from azure.identity import DefaultAzureCredential

app = Flask(__name__)

SERVER = "sql-webapp-dev-2026.database.windows.net"
DATABASE = "sqldb-webapp-dev"

def get_connection():
    credential = DefaultAzureCredential()
    token = credential.get_token(
        "https://database.windows.net/.default"
    ).token

    token_bytes = token.encode("utf-16-le")
    token_struct = struct.pack(
        f"<I{len(token_bytes)}s",
        len(token_bytes),
        token_bytes
    )

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
        attrs_before={
            SQL_COPT_SS_ACCESS_TOKEN: token_struct
        }
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
    <html>
    <head>
        <title>Azure Cloud Portfolio</title>
    </head>

    <body>

    <h1>Azure Cloud Portfolio</h1>
    <h2>Cloud Tasks App By Abdulsattar Homsi</h2>	

    <h2>Add Cloud Task</h2>

    <form method="POST" action="/add">

        <label>Title:</label><br>
        <input type="text" name="title" required>

        <br><br>

        <label>Description:</label><br>
        <input type="text" name="description">

        <br><br>

        <button type="submit">
            Add Task
        </button>

    </form>

    <hr>

    <h2>Cloud Tasks</h2>

    <table border="1" cellpadding="8">

        <tr>
            <th>ID</th>
            <th>Title</th>
            <th>Description</th>
            <th>Status</th>
            <th>Created</th>
            <th>Actions</th>
        </tr>
    """

    for task in tasks:

        html += f"""
        <tr>

            <td>{task.Id}</td>

            <td>{task.Title}</td>

            <td>{task.Description or ""}</td>

            <td>{task.Status}</td>

            <td>{task.CreatedAt}</td>

            <td>

                <form
                    method="POST"
                    action="/complete/{task.Id}"
                    style="display:inline;"
                >

                    <button type="submit">
                        Complete
                    </button>

                </form>

                <form
                    method="POST"
                    action="/delete/{task.Id}"
                    style="display:inline;"
                >

                    <button type="submit">
                        Delete
                    </button>

                </form>

            </td>

        </tr>
        """

    html += """

    </table>

    </body>
    </html>
    """

    return html


@app.route("/add", methods=["POST"])
def add_task():

    title = request.form["title"]
    description = request.form["description"]

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO CloudTasks
        (Title, Description, Status)
        VALUES (?, ?, ?)
        """,
        title,
        description,
        "Pending"
    )

    conn.commit()

    cursor.close()
    conn.close()

    return redirect(url_for("home"))


@app.route("/complete/<int:task_id>", methods=["POST"])
def complete_task(task_id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE CloudTasks
        SET Status = 'Completed'
        WHERE Id = ?
        """,
        task_id
    )

    conn.commit()

    cursor.close()
    conn.close()

    return redirect(url_for("home"))


@app.route("/delete/<int:task_id>", methods=["POST"])
def delete_task(task_id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        DELETE FROM CloudTasks
        WHERE Id = ?
        """,
        task_id
    )

    conn.commit()

    cursor.close()
    conn.close()

    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run()