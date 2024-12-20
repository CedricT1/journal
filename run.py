from app import create_app, db
from app.models import RSSFeed, LLMConfig, WeatherConfig, Bulletin

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'RSSFeed': RSSFeed,
        'LLMConfig': LLMConfig,
        'WeatherConfig': WeatherConfig,
        'Bulletin': Bulletin
    }

if __name__ == '__main__':
    app.run(debug=True)