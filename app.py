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
        final_video_path = "output_video.mp4"

        for file in [audio_path, image_path, final_video_path]:
            if os.path.exists(file):
                os.remove(file)

        # 1. สร้างเสียงพากย์
        print("1. Generating audio with gTTS...")
        tts = gTTS(text=text, lang='th')
        tts.save(audio_path)

        # 2. ดาวน์โหลดรูปภาพ
        print("2. Downloading image...")
        img_response = requests.get(image_url)
        with open(image_path, 'wb') as f:
            f.write(img_response.content)

        # 3. ลองเรียก Hugging Face แบบป้องกันพัง (Try-Except)
        hf_video_path = None
        try:
            print("3. Connecting to Hugging Face AI Video...")
            client = Client("stabilityai/stable-video-diffusion")
            result = client.predict(
                image_path=image_path,
                seed=42,
                motion_bucket_id=127,
                fps_id=6,
                api_name="/image_to_video"
            )
            hf_video_path = result[0] if isinstance(result, (list, tuple)) else result
        except Exception as hf_err:
            print("Hugging Face failed, switching to fallback mode (Ken Burns Zoom):", hf_err)

        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

        # 4. ถ้า Hugging Face สำเร็จ ให้รวมวิดีโอขยับ + เสียง
        if hf_video_path and os.path.exists(hf_video_path):
            print("Combining AI Video and Audio...")
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
        else:
            # สำรองฉุกเฉิน: ถ้า Hugging Face ล่ม ระบบจะใช้ภาพนิ่งซูม (Ken Burns) แทนทันที เพื่อไม่ให้งานพัง
            print("Fallback: Using Cinematic Zoom effect instead.")
            ffmpeg_cmd = [
                ffmpeg_exe, '-y',
                '-loop', '1',
                '-i', image_path,
                '-i', audio_path,
                '-vf', "zoompan=z='min(zoom+0.0015,1.5)':d=700:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)',scale=720:1280",
                '-c:v', 'libx264',
                '-c:a', 'aac',
                '-b:a', '192k',
                '-pix_fmt', 'yuv420p',
                '-shortest',
                final_video_path
            ]

        subprocess.run(ffmpeg_cmd, check=True, capture_output=True, text=True)

        print("Done! Sending video back to n8n.")
        return send_file(final_video_path, mimetype='video/mp4', as_attachment=True, download_name='final_animated_series.mp4')

    except Exception as e:
        print("Fatal Error:", str(e))
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
