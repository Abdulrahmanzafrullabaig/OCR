from flask import Flask, request, jsonify, render_template
import easyocr
import os
import argostranslate.package
import argostranslate.translate

class TranslationApp:
    def __init__(self):
        self.app = Flask(__name__)
        
        # Initialize EasyOCR readers for compatible language groups
        self.japanese_reader = easyocr.Reader(['en', 'ja'], gpu=False)  # Japanese and English
        self.other_languages_reader = easyocr.Reader(['en', 'de', 'fr', 'es'], gpu=False)  # English, German, French, Spanish
        
        # Install Argos Translate language models for specific languages
        self.setup_translation()
        
        # Define Flask routes
        self.setup_routes()

    def setup_translation(self):
        """Install Argos Translate language models for specific languages."""
        try:
            # Update the package index
            argostranslate.package.update_package_index()

            # Define supported language codes
            supported_languages = ['en', 'ja', 'de', 'fr', 'es']

            # Get available and installed packages
            available_packages = argostranslate.package.get_available_packages()
            installed_packages = argostranslate.package.get_installed_packages()

            # Install missing packages for supported languages
            for package in available_packages:
                if package.from_code in supported_languages and package.to_code in supported_languages:
                    # Check if the package is already installed
                    is_installed = any(
                        installed.from_code == package.from_code and installed.to_code == package.to_code
                        for installed in installed_packages
                    )
                    if not is_installed:
                        print(f"Installing language model: {package.from_code} -> {package.to_code}")
                        argostranslate.package.install_from_path(package.download())
        except Exception as e:
            print(f"Error setting up translation: {str(e)}")

    def extract_text(self, image_path, lang_group="other"):
        """Extract text from an image using EasyOCR."""
        if lang_group == "japanese":
            result = self.japanese_reader.readtext(image_path, detail=0)  # Extract only the text
        else:
            result = self.other_languages_reader.readtext(image_path, detail=0)  # Extract only the text
        return " ".join(result)  # Join all detected text into a single string

    def translate(self, text, target_code):
        """Translate text using Argos Translate."""
        try:
            installed_languages = argostranslate.translate.get_installed_languages()

            # Find the target language
            target_lang = next((lang for lang in installed_languages if lang.code == target_code), None)
            if not target_lang:
                return f"Error: Target language '{target_code}' is not installed."

            # Translate the text (auto-detects source language)
            translated_text = target_lang.translate(text)
            return translated_text
        except Exception as e:
            return f"Error: Unable to translate text. {str(e)}"

    def setup_routes(self):
        """Define Flask routes."""

        @self.app.route('/')
        def index():
            """Serve the main HTML page."""
            return render_template('index.html')

        @self.app.route('/upload', methods=['POST'])
        def upload():
            """Handle image upload and text extraction."""
            if 'file' not in request.files:
                return jsonify({"error": "No file uploaded"}), 400

            file = request.files['file']
            if not file.filename:
                return jsonify({"error": "Empty file"}), 400

            # Save the uploaded file temporarily
            os.makedirs("uploads", exist_ok=True)
            image_path = os.path.join("uploads", file.filename)

            try:
                file.save(image_path)
                
                # Extract text using the appropriate reader
                extracted_text = self.extract_text(image_path, lang_group="other")  # Default to "other" languages
                
                os.remove(image_path)  # Clean up the temporary file

                if not extracted_text.strip():
                    return jsonify({"error": "No text found in the image."}), 400

                return jsonify({"extracted_text": extracted_text})
            except Exception as e:
                return jsonify({"error": f"An error occurred: {str(e)}"}), 500

        @self.app.route('/translate', methods=['POST'])
        def translate_route():
            """Handle text translation."""
            data = request.json
            text = data.get("text")
            target_language = data.get("target_language")

            if not text or not target_language:
                return jsonify({"error": "Missing parameters: 'text' or 'target_language'"}), 400

            try:
                translated_text = self.translate(text, target_language)
                return jsonify({"translated_text": translated_text})
            except Exception as e:
                return jsonify({"error": f"Translation failed: {str(e)}"}), 500

    def run(self, debug=True, port=5000):
        """Run the Flask app."""
        self.app.run(debug=debug, port=port)


if __name__ == "__main__":
    app = TranslationApp()
    app.run()