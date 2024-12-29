from app.tasks import cleanup_audio_files
from app import create_app

app = create_app()
with app.app_context():
    cleanup_audio_files() 