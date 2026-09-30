from flask import Flask, jsonify
from flask_cors import CORS

from config import Config
from extensions import db, jwt


def create_app(config_overrides=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if config_overrides:
        app.config.update(config_overrides)

    db.init_app(app)
    jwt.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})

    from routes import activities, analytics, auth, classrooms, lessons, profiles, reviews, support
    for module in (auth, classrooms, profiles, lessons, reviews, activities, analytics, support):
        app.register_blueprint(module.bp)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "ai_mode": "claude" if app.config["ANTHROPIC_API_KEY"] else "demo"})

    @app.errorhandler(404)
    def not_found(_e):
        return jsonify({"error": "not found"}), 404

    @app.errorhandler(500)
    def server_error(_e):
        return jsonify({"error": "internal server error"}), 500

    @jwt.unauthorized_loader
    def missing_token(reason):
        return jsonify({"error": "login required", "detail": reason}), 401

    @jwt.invalid_token_loader
    def bad_token(reason):
        return jsonify({"error": "invalid token", "detail": reason}), 401

    @jwt.expired_token_loader
    def expired(_h, _p):
        return jsonify({"error": "session expired, please log in again"}), 401

    with app.app_context():
        import models  # noqa: F401  (registers tables)
        db.create_all()
    return app


if __name__ == "__main__":
    create_app().run(debug=True, port=5000)
