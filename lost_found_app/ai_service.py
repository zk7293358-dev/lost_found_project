import torch
from torchvision import models, transforms
from PIL import Image
import time
import logging
import os
from django.conf import settings

logger = logging.getLogger(__name__)

class PyTorchAIClassificationService:
    def __init__(self):
        self.model = None
        self.classes = []
        self.transform = None
        self.model_loaded = False
        self.model_version = "resnet101"
        self.load_model()
    
    def load_model(self):
        """Load the ResNet101 model and classes"""
        try:
            # Initialize ResNet101 model (pretrained on ImageNet)
            self.model = models.resnet101(pretrained=True)
            self.model.eval()

            # Load ImageNet class names from txt file if available
            classes_path = os.path.join(settings.BASE_DIR, 'ai_models', 'imagenet_classes.txt')
            if os.path.exists(classes_path):
                with open(classes_path) as f:
                    self.classes = [line.strip() for line in f.readlines()]
                logger.info("Loaded imagenet_classes.txt successfully")
            else:
                # Fallback to default built-in weights metadata
                from torchvision.models import ResNet101_Weights
                self.classes = ResNet101_Weights.IMAGENET1K_V2.meta["categories"]
                logger.warning("imagenet_classes.txt not found. Using default ImageNet categories")

            # Define transformations same as Streamlit version
            self.transform = transforms.Compose([
                transforms.Resize(256),
                transforms.CenterCrop(224),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225]
                )
            ])

            self.model_loaded = True
            logger.info("PyTorch AI Service (ResNet101 pretrained) initialized successfully")

        except Exception as e:
            logger.error(f"Failed to load PyTorch model: {str(e)}")
            self.model_loaded = False

    def preprocess_image(self, image_path):
        """Preprocess image for model prediction"""
        try:
            if isinstance(image_path, str):
                image = Image.open(image_path)
            else:
                image = Image.open(image_path)

            if image.mode != 'RGB':
                image = image.convert('RGB')

            return image
        except Exception as e:
            logger.error(f"Image preprocessing failed: {str(e)}")
            raise e

    def predict(self, image):
        """Make prediction using pretrained ResNet101"""
        if not self.model_loaded:
            raise Exception("Model not loaded properly")

        try:
            # Preprocess and batchify
            processed_image = self.transform(image)
            batch_t = torch.unsqueeze(processed_image, 0)

            # Predict
            with torch.no_grad():
                start_time = time.time()
                out = self.model(batch_t)
                processing_time = time.time() - start_time

                # Compute probabilities and sort
                probabilities = torch.nn.functional.softmax(out, dim=1)[0] * 100
                _, indices = torch.sort(out, descending=True)
                indices = indices[0][:5]

                predictions = []
                for idx in indices:
                    label = self.classes[idx]
                    prob = probabilities[idx].item()
                    predictions.append({
                        'category': label,
                        'confidence': prob
                    })

                return predictions, processing_time

        except Exception as e:
            logger.error(f"Prediction failed: {str(e)}")
            raise e

    def classify_image(self, image_path):
        """Classify image and return formatted results"""
        if not self.model_loaded:
            return {
                'suggested_category': 'unknown',
                'confidence': 0.0,
                'top_predictions': {'predictions': []},
                'processing_time': 0.0,
                'error': 'Model not loaded'
            }

        try:
            image = self.preprocess_image(image_path)
            predictions, processing_time = self.predict(image)

            result = {
                'suggested_category': predictions[0]['category'] if predictions else 'unknown',
                'confidence': predictions[0]['confidence'] if predictions else 0.0,
                'top_predictions': {
                    'predictions': predictions,
                    'count': len(predictions)
                },
                'processing_time': processing_time,
                'model_version': self.model_version
            }

            self.log_classification(image_path, result)
            return result

        except Exception as e:
            logger.error(f"Image classification failed: {str(e)}")
            return {
                'suggested_category': 'unknown',
                'confidence': 0.0,
                'top_predictions': {'predictions': []},
                'processing_time': 0.0,
                'error': str(e)
            }

    def log_classification(self, image_path, result):
        """Optional: Log classification result to database"""
        try:
            from .models import AIClassificationLog
            AIClassificationLog.objects.create(
                image_path=str(image_path),
                predicted_category=result['suggested_category'],
                confidence_score=result['confidence'],
                top_predictions=result['top_predictions'],
                model_version=result['model_version'],
                processing_time=result['processing_time']
            )
        except Exception as e:
            logger.warning(f"Failed to log classification: {str(e)}")

    def real_time_classify(self, image_file):
        """Real-time classification for API endpoint"""
        try:
            temp_path = os.path.join(settings.MEDIA_ROOT, 'temp', f'temp_{int(time.time())}.jpg')
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)

            with open(temp_path, 'wb') as f:
                for chunk in image_file.chunks():
                    f.write(chunk)

            result = self.classify_image(temp_path)

            try:
                os.remove(temp_path)
            except:
                pass

            return result

        except Exception as e:
            logger.error(f"Real-time classification failed: {str(e)}")
            raise e


# Global instance
pytorch_ai_service = PyTorchAIClassificationService()
