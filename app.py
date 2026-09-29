import os
import subprocess
import requests
from flask import Flask, request, jsonify, send_file
from gtts import gTTS
import imageio_ffmpeg

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
        video_path = "output_video.mp4"

        # เคลียร์ไฟล์เก่าทิ้ง
        for file in [audio_path, image_path, video_path]:
            if os.path.exists(file):
                os.remove(file)

        # 1. สร้างเสียงพากย์ด้วย Google TTS (เสถียรกว่าบน Cloud)
        print("Generating audio with gTTS...")
        tts = gTTS(text=text, lang='th')
        tts.save(audio_path)

        # 2. ดาวน์โหลดรูปภาพ
        print("Downloading image...")
        img_response = requests.get(image_url)
        if img_response.status_code == 200:
            with open(image_path, 'wb') as f:
                f.write(img_response.content)
        else:
            return jsonify({"error": "Failed to download image"}), 400

        # 3. ดึงเส้นทางโปรแกรม ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

        # 4. ตัดต่อภาพและเสียงเข้าด้วยกัน
        print("Generating video with ffmpeg...")
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
            video_path
        ]
        
        try:
            subprocess.run(ffmpeg_cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            print("FFMPEG Error:\n", e.stderr)
            return jsonify({"error": "FFMPEG failed", "details": e.stderr}), 500

        # 5. ส่งไฟล์ MP4 กลับไปให้ n8n
        return send_file(video_path, mimetype='video/mp4', as_attachment=True, download_name='final_series.mp4')

    except Exception as e:
        print("Error:", e)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
