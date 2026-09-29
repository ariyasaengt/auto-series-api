import os
import subprocess
import requests
from flask import Flask, request, jsonify, send_file
from gtts import gTTS
import imageio_ffmpeg
from gradio_client import Client

app = Flask(__name__)

@app.route('/generate', methods=['POST'])
def generate_video():
    try:
        data = request.get_json(force=True)
        text = data.get('text', '').strip()
        image_url = data.get('image_url', '').strip()

        if not text or not image_url:
            return jsonify({"error": "Missing text or image_url"}), 400

        audio_path = "temp_audio.mp3"
        image_path = "temp_image.jpg"
        silent_video_path = "temp_silent.mp4"
        final_video_path = "output_video.mp4"

        for file in [audio_path, image_path, silent_video_path, final_video_path]:
            if os.path.exists(file):
                os.remove(file)

        # 1. สร้างเสียงพากย์ด้วย gTTS
        print("1. Generating audio with gTTS...")
        tts = gTTS(text=text, lang='th')
        tts.save(audio_path)

        # 2. ดาวน์โหลดรูปภาพจาก Pollinations
        print("2. Downloading image...")
        img_response = requests.get(image_url)
        with open(image_path, 'wb') as f:
            f.write(img_response.content)

        # 3. ส่งภาพไปแปลงเป็นวิดีโอผ่าน Hugging Face Space (ฟรี)
        # เราใช้โมเดลยอดฮิต Stable Video Diffusion บนสาธารณะ
        print("3. Generating AI Video via Hugging Face (Please wait, public servers can take 1-3 minutes)...")
        client = Client("stabilityai/stable-video-diffusion")
        result = client.predict(
            image_path=image_path,
            seed=42,
            motion_bucket_id=127,
            fps_id=6,
            api_name="/image_to_video"
        )
        
        # ผลลัพธ์ที่ได้จาก Gradio จะเป็น path ของไฟล์วิดีโอชั่วคราว
        hf_video_path = result[0] if isinstance(result, (list, tuple)) else result

        # 4. รวมวิดีโออนิเมชันและเสียงพากย์เข้าด้วยกัน (วนลูปวิดีโอให้จบตามเสียง)
        print("4. Combining Video and Audio with ffmpeg...")
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        ffmpeg_cmd = [
            ffmpeg_exe, '-y',
            '-stream_loop', '-1',
            '-i', hf_video_path,
            '-i', audio_path,
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-pix_fmt', 'yuv420p',
            '-shortest',
            final_video_path
        ]
        
        subprocess.run(ffmpeg_cmd, check=True, capture_output=True, text=True)

        print("Done! Sending animated video back to n8n.")
        return send_file(final_video_path, mimetype='video/mp4', as_attachment=True, download_name='final_animated_series.mp4')

    except Exception as e:
        print("Error:", e)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
