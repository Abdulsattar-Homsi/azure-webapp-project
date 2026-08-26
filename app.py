from flask import Flask, request, redirect, url_for, send_file
import struct
import pyodbc
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceNotFoundError
from werkzeug.utils import secure_filename
import io
import time

# ---------------------------------------------------------
# Azure Storage Configuration
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# Flask Application
# ---------------------------------------------------------

app = Flask(__name__)


# ---------------------------------------------------------
# Azure SQL Configuration
# ---------------------------------------------------------

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

    # Retry transient Azure SQL connection failures
    max_retries = 3

    for attempt in range(max_retries):
        try:
            return pyodbc.connect(
                connection_string,
                attrs_before={
                    SQL_COPT_SS_ACCESS_TOKEN: token_struct
                },
                timeout=15
            )

        except pyodbc.OperationalError:
            if attempt == max_retries - 1:
                raise

            time.sleep(3)

# ---------------------------------------------------------
# Home Page
# ---------------------------------------------------------

@app.route("/")
def home():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            Id,
            Title,
            Description,
            Status,
            CreatedAt,
            FileName
        FROM CloudTasks
        ORDER BY Id DESC
    """)

    tasks = cursor.fetchall()

    cursor.close()
    conn.close()

    total_tasks = len(tasks)

    completed_tasks = sum(
        1 for task in tasks
        if task.Status == "Completed"
    )

    pending_tasks = total_tasks - completed_tasks

    html = f"""
    <!DOCTYPE html>

    <html lang="en">

    <head>

        <meta charset="UTF-8">

        <meta
            name="viewport"
            content="width=device-width, initial-scale=1.0"
        >

        <title>CloudTask</title>

        <style>

            * {{
                box-sizing: border-box;
            }}

            body {{
                margin: 0;
                font-family:
                    -apple-system,
                    BlinkMacSystemFont,
                    "Segoe UI",
                    Roboto,
                    Arial,
                    sans-serif;

                background: #f5f7fb;
                color: #1f2937;
            }}

            .page {{
                width: 92%;
                max-width: 1100px;
                margin: 40px auto;
            }}

            /* -----------------------------------
               Header
            ----------------------------------- */

            .header {{
                background: white;
                border-radius: 18px;
                padding: 30px 34px;
                margin-bottom: 24px;
                border: 1px solid #e5e7eb;
                box-shadow: 0 6px 20px rgba(0,0,0,0.04);
            }}

            .header-top {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 20px;
            }}

            .brand {{
                display: flex;
                align-items: center;
                gap: 16px;
            }}

            .cloud-icon {{
                width: 58px;
                height: 58px;
                border-radius: 15px;
                background: #0078d4;
                color: white;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 29px;
            }}

            .brand h1 {{
                margin: 0;
                font-size: 30px;
                color: #111827;
            }}

            .subtitle {{
                margin-top: 4px;
                color: #6b7280;
                font-size: 15px;
            }}

            .azure-badge {{
                background: #eef6ff;
                color: #0067b8;
                padding: 9px 15px;
                border-radius: 999px;
                font-size: 13px;
                font-weight: 600;
                white-space: nowrap;
            }}

            .author {{
                margin-top: 22px;
                padding-top: 18px;
                border-top: 1px solid #e5e7eb;
                color: #6b7280;
                font-size: 14px;
            }}

            .author strong {{
                color: #374151;
            }}

            /* -----------------------------------
               Statistics
            ----------------------------------- */

            .stats {{
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 16px;
                margin-bottom: 24px;
            }}

            .stat-card {{
                background: white;
                border: 1px solid #e5e7eb;
                border-radius: 14px;
                padding: 18px 22px;
            }}

            .stat-title {{
                color: #6b7280;
                font-size: 13px;
                margin-bottom: 5px;
            }}

            .stat-value {{
                font-size: 26px;
                font-weight: 700;
            }}

            /* -----------------------------------
               Main Cards
            ----------------------------------- */

            .card {{
                background: white;
                border: 1px solid #e5e7eb;
                border-radius: 18px;
                padding: 28px;
                margin-bottom: 24px;
                box-shadow: 0 6px 20px rgba(0,0,0,0.03);
            }}

            .section-title {{
                margin: 0 0 22px 0;
                font-size: 21px;
                display: flex;
                align-items: center;
                gap: 9px;
            }}

            /* -----------------------------------
               Form
            ----------------------------------- */

            .form-grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
            }}

            .form-group {{
                margin-bottom: 18px;
            }}

            .form-group.full {{
                grid-column: 1 / -1;
            }}

            label {{
                display: block;
                margin-bottom: 7px;
                font-size: 14px;
                font-weight: 600;
                color: #374151;
            }}

            input[type="text"] {{
                width: 100%;
                padding: 12px 14px;
                border: 1px solid #d1d5db;
                border-radius: 9px;
                font-size: 15px;
                outline: none;
                background: #fff;
            }}

            input[type="text"]:focus {{
                border-color: #0078d4;
                box-shadow: 0 0 0 3px rgba(0,120,212,0.12);
            }}

            input[type="file"] {{
                width: 100%;
                border: 1px dashed #cbd5e1;
                padding: 12px;
                border-radius: 9px;
                background: #f8fafc;
            }}

            .button-row {{
                display: flex;
                justify-content: flex-end;
                margin-top: 8px;
            }}

            .btn {{
                border: none;
                padding: 10px 17px;
                border-radius: 8px;
                cursor: pointer;
                font-weight: 600;
                font-size: 14px;
                text-decoration: none;
                display: inline-block;
            }}

            .btn-primary {{
                background: #0078d4;
                color: white;
            }}

            .btn-primary:hover {{
                background: #0067b8;
            }}

            .btn-complete {{
                background: #ecfdf3;
                color: #067647;
                border: 1px solid #abefc6;
            }}

            .btn-delete {{
                background: #fff1f2;
                color: #be123c;
                border: 1px solid #fecdd3;
            }}

            /* -----------------------------------
               Tasks
            ----------------------------------- */

            .tasks-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
            }}

            .tasks-header .section-title {{
                margin: 0;
            }}

            .task-count {{
                color: #6b7280;
                font-size: 14px;
            }}

            .task-card {{
                border: 1px solid #e5e7eb;
                border-radius: 13px;
                padding: 20px;
                margin-bottom: 14px;
                transition: 0.15s ease;
            }}

            .task-card:hover {{
                border-color: #b8d8f3;
                background: #fbfdff;
            }}

            .task-top {{
                display: flex;
                justify-content: space-between;
                gap: 20px;
                align-items: flex-start;
            }}

            .task-title {{
                font-size: 18px;
                font-weight: 650;
                margin-bottom: 6px;
            }}

            .task-description {{
                color: #6b7280;
                font-size: 14px;
                line-height: 1.5;
            }}

            .status {{
                padding: 6px 11px;
                border-radius: 999px;
                font-size: 12px;
                font-weight: 700;
                white-space: nowrap;
            }}

            .status-completed {{
                background: #ecfdf3;
                color: #067647;
            }}

            .status-pending {{
                background: #fff7ed;
                color: #c2410c;
            }}

            .task-bottom {{
                margin-top: 17px;
                padding-top: 15px;
                border-top: 1px solid #f0f1f3;

                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 15px;
                flex-wrap: wrap;
            }}

            .task-meta {{
                display: flex;
                gap: 18px;
                flex-wrap: wrap;
                color: #6b7280;
                font-size: 13px;
            }}

            .attachment {{
                color: #0078d4;
                text-decoration: none;
                font-weight: 600;
            }}

            .attachment:hover {{
                text-decoration: underline;
            }}

            .actions {{
                display: flex;
                gap: 8px;
                align-items: center;
            }}

            .actions form {{
                margin: 0;
            }}

            .empty-state {{
                text-align: center;
                color: #6b7280;
                padding: 35px 20px;
            }}

            /* -----------------------------------
               Footer
            ----------------------------------- */

            footer {{
                text-align: center;
                color: #9ca3af;
                font-size: 13px;
                padding: 8px 0 30px 0;
                line-height: 1.8;
            }}

            footer strong {{
                color: #6b7280;
            }}

            /* -----------------------------------
               Responsive
            ----------------------------------- */

            @media (max-width: 720px) {{

                .page {{
                    width: 94%;
                    margin-top: 20px;
                }}

                .header-top {{
                    align-items: flex-start;
                    flex-direction: column;
                }}

                .stats {{
                    grid-template-columns: 1fr;
                }}

                .form-grid {{
                    grid-template-columns: 1fr;
                }}

                .form-group.full {{
                    grid-column: auto;
                }}

                .task-top {{
                    flex-direction: column;
                }}

                .task-bottom {{
                    flex-direction: column;
                    align-items: flex-start;
                }}

                .actions {{
                    width: 100%;
                }}

                .actions form {{
                    flex: 1;
                }}

                .actions button {{
                    width: 100%;
                }}
            }}

        </style>

    </head>


    <body>

        <main class="page">

            <!-- Header -->

            <section class="header">

                <div class="header-top">

                    <div class="brand">

                        <div class="cloud-icon">
                            ☁
                        </div>

                        <div>

                            <h1>CloudTask</h1>

                            <div class="subtitle">
                                Simple Task Management in the Cloud
                            </div>

                        </div>

                    </div>

                    <div class="azure-badge">
                        Microsoft Azure Powered
                    </div>

                </div>

                

            </section>


            <!-- Statistics -->

            <section class="stats">

                <div class="stat-card">
                    <div class="stat-title">Total Tasks</div>
                    <div class="stat-value">{total_tasks}</div>
                </div>

                <div class="stat-card">
                    <div class="stat-title">Pending</div>
                    <div class="stat-value">{pending_tasks}</div>
                </div>

                <div class="stat-card">
                    <div class="stat-title">Completed</div>
                    <div class="stat-value">{completed_tasks}</div>
                </div>

            </section>


            <!-- Add Task -->

            <section class="card">

                <h2 class="section-title">
                    ➕ Add New Task
                </h2>

                <form
                    method="POST"
                    action="/add"
                    enctype="multipart/form-data"
                >

                    <div class="form-grid">

                        <div class="form-group">

                            <label for="title">
                                Title
                            </label>

                            <input
                                id="title"
                                type="text"
                                name="title"
                                placeholder="Enter task title"
                                required
                            >

                        </div>


                        <div class="form-group">

                            <label for="description">
                                Description
                            </label>

                            <input
                                id="description"
                                type="text"
                                name="description"
                                placeholder="Describe your task"
                            >

                        </div>


                        <div class="form-group full">

                            <label for="file">
                                Attachment
                            </label>

                            <input
                                id="file"
                                type="file"
                                name="file"
                            >

                        </div>

                    </div>


                    <div class="button-row">

                        <button
                            type="submit"
                            class="btn btn-primary"
                        >
                            + Add Task
                        </button>

                    </div>

                </form>

            </section>


            <!-- Tasks -->

            <section class="card">

                <div class="tasks-header">

                    <h2 class="section-title">
                        📋 My Tasks
                    </h2>

                    <div class="task-count">
                        {total_tasks} task{"s" if total_tasks != 1 else ""}
                    </div>

                </div>
    """

    # ---------------------------------------------------------
    # Build Task Cards
    # ---------------------------------------------------------

    if not tasks:

        html += """
            <div class="empty-state">
                No tasks yet. Add your first cloud task above.
            </div>
        """

    else:

        for task in tasks:

            status_class = (
                "status-completed"
                if task.Status == "Completed"
                else "status-pending"
            )

            status_icon = (
                "✓"
                if task.Status == "Completed"
                else "●"
            )

            description = task.Description or "No description"

            created = task.CreatedAt.strftime(
                "%d %b %Y · %H:%M"
            )

            if task.FileName:

                attachment_html = f"""
                    📎
                    <a
                        class="attachment"
                        href="/download/{task.Id}"
                    >
                        {task.FileName}
                    </a>
                """

            else:

                attachment_html = """
                    📎 No attachment
                """

            if task.Status == "Completed":

                complete_button = ""

            else:

                complete_button = f"""
                    <form
                        method="POST"
                        action="/complete/{task.Id}"
                    >

                        <button
                            type="submit"
                            class="btn btn-complete"
                        >
                            ✓ Complete
                        </button>

                    </form>
                """

            html += f"""
                <article class="task-card">

                    <div class="task-top">

                        <div>

                            <div class="task-title">
                                {task.Title}
                            </div>

                            <div class="task-description">
                                {description}
                            </div>

                        </div>

                        <span class="status {status_class}">
                            {status_icon} {task.Status}
                        </span>

                    </div>


                    <div class="task-bottom">

                        <div class="task-meta">

                            <span>
                                🕒 {created}
                            </span>

                            <span>
                                {attachment_html}
                            </span>

                        </div>


                        <div class="actions">

                            {complete_button}

                            <form
                                method="POST"
                                action="/delete/{task.Id}"
                            >

                                <button
                                    type="submit"
                                    class="btn btn-delete"
                                >
                                    Delete
                                </button>

                            </form>

                        </div>

                    </div>

                </article>
            """

    html += """

            </section>


            <!-- Footer -->

            <footer>

                <strong>
                    CloudTask
                </strong>

                <br>

                Built with Python Flask &amp; Microsoft Azure

                <br>

                © 2026 Abdulsattar Homsi

            </footer>

        </main>

    </body>

    </html>
    """

    return html


# ---------------------------------------------------------
# Add Task
# ---------------------------------------------------------

@app.route("/add", methods=["POST"])
def add_task():

    title = request.form["title"]
    description = request.form["description"]

    file = request.files.get("file")

    filename = None

    if file and file.filename:

        filename = secure_filename(
            file.filename
        )

        blob_service_client = (
            get_blob_service_client()
        )

        blob_client = (
            blob_service_client.get_blob_client(
                container=CONTAINER_NAME,
                blob=filename
            )
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
        (
            Title,
            Description,
            Status,
            FileName
        )
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

    return redirect(
        url_for("home")
    )


# ---------------------------------------------------------
# Complete Task
# ---------------------------------------------------------

@app.route(
    "/complete/<int:task_id>",
    methods=["POST"]
)
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

    return redirect(
        url_for("home")
    )


# ---------------------------------------------------------
# Delete Task
# ---------------------------------------------------------

@app.route(
    "/delete/<int:task_id>",
    methods=["POST"]
)
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

    return redirect(
        url_for("home")
    )


# ---------------------------------------------------------
# Download Attachment
# ---------------------------------------------------------

@app.route(
    "/download/<int:task_id>"
)
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

        return (
            "File not found",
            404
        )

    blob_service_client = (
        get_blob_service_client()
    )

    blob_client = (
        blob_service_client.get_blob_client(
            container=CONTAINER_NAME,
            blob=task.FileName
        )
    )

    try:

        blob_data = (
            blob_client
            .download_blob()
            .readall()
        )

    except ResourceNotFoundError:

        return (
            "The attachment no longer exists "
            "in Blob Storage.",
            404
        )

    return send_file(
        io.BytesIO(blob_data),
        as_attachment=True,
        download_name=task.FileName
    )


# ---------------------------------------------------------
# Start Application
# ---------------------------------------------------------

if __name__ == "__main__":
    app.run()