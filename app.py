from flask import Flask, request, redirect, url_for
import struct
import pyodbc
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceNotFoundError
from werkzeug.utils import secure_filename
from flask import send_file
import io

STORAGE_ACCOUNT_NAME = "stwebappdev4728"
CONTAINER_NAME = "taskfiles"

def get_blob_service_client():
    credential = DefaultAzureCredential()

    account_url = (
        f"https://{STORAGE_ACCOUNT_NAME}.blob.core.windows.net"
    )

    return BlobServiceClient(
        account_url=account_url,
        credential=credential
    )

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
	SELECT Id, Title, Description, Status, CreatedAt, FileName
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

    <form method="POST" action="/add"
      	enctype="multipart/form-data">

        <label>Title:</label><br>
        <input type="text" name="title" required>

        <br><br>

        <label>Description:</label><br>
        <input type="text" name="description">

        <br><br>

	<label>Attachment:</label><br>
	<input type="file" name="file">

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
	    <th>Attachment</th>
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
    		{
        	     f'<a href="/download/{task.Id}">{task.FileName}</a>'
        	     if task.FileName
        	     else "No file"
    		}

	    </td>

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

    file = request.files.get("file")
    filename = None

    if file and file.filename:

        filename = secure_filename(file.filename)

        blob_service_client = get_blob_service_client()

        blob_client = blob_service_client.get_blob_client(
            container=CONTAINER_NAME,
            blob=filename
        )

        blob_client.upload_blob(
            file,
            overwrite=True
        )

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO CloudTasks
        (Title, Description, Status, FileName)
        VALUES (?, ?, ?, ?)
        """,
        title,
        description,
        "Pending",
        filename
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


@app.route("/upload", methods=["POST"])
def upload_file():

    file = request.files["file"]

    if file.filename == "":
        return redirect(url_for("home"))

    filename = secure_filename(file.filename)

    blob_service_client = get_blob_service_client()

    blob_client = blob_service_client.get_blob_client(
        container=CONTAINER_NAME,
        blob=filename
    )

    blob_client.upload_blob(
        file,
        overwrite=True
    )

    return redirect(url_for("home"))


@app.route("/download/<int:task_id>")
def download_file(task_id):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT FileName
        FROM CloudTasks
        WHERE Id = ?
        """,
        task_id
    )

    task = cursor.fetchone()

    cursor.close()
    conn.close()

    if not task or not task.FileName:
        return "File not found", 404

    blob_service_client = get_blob_service_client()

    blob_client = blob_service_client.get_blob_client(
        container=CONTAINER_NAME,
        blob=task.FileName
    )

    try:
        blob_data = blob_client.download_blob().readall()

    except ResourceNotFoundError:
        return "The attachment no longer exists in Blob Storage.", 404

    return send_file(
        io.BytesIO(blob_data),
        as_attachment=True,
        download_name=task.FileName
    )



if __name__ == "__main__":
    app.run()