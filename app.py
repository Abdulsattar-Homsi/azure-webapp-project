from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return """
    <h1>Azure Cloud Portfolio</h1>
    <h2>My First Azure Web Application</h2>

    <p>This application is running on Microsoft Azure App Service.</p>

    <p>Environment: Development</p>

    <p>Deployed automatically using GitHub Actions CI/CD.</p>
    """

if __name__ == "__main__":
    app.run()