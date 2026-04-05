import ollama
import base64
import os

def image_to_base64(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Image not found: {path}")
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def describe_image(image_path):
    try:
        image_b64 = image_to_base64(image_path)
        
        print(f"Processing image: {image_path}...")
        response = ollama.chat(
            model="moondream:1.8b",
            messages=[{
                'role': 'user',
                'content': 'Describe this robot camera image for navigation.',
                'images': [image_b64]
            }]
        )
        
        return response['message']['content']
    except Exception as e:
        return f"Error: {str(e)}"

if __name__ == "__main__":
    image_path = "robot_camera.jpg"
    description = describe_image(image_path)
    print("\nModel Output:")
    print("=" * 20)
    print(description)
    print("=" * 20)
