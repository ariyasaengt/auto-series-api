import os
import subprocess
import requests
from flask import Flask, request, jsonify, send_file

app = Flask(__name__)

@app.route('/generate', methods=['POST'])
def generate_video():
    try:
        # 1. รับข้อมูล JSON จาก n8n (บังคับอ่านค่าป้องกัน None)
        data = request.get_json(force=True)
        text = data.get('text', '').strip()
        image_url = data.get('image_url', '').strip()

        # ตรวจสอบว่ามีข้อมูลส่งมาครบถ้วนหรือไม่
        if not text or not image_url:
            return jsonify({"error": "Missing text or image_url"}), 400

        # 2. กำหนดชื่อไฟล์ชั่วคราว
        audio_path = "temp_audio.mp3"
        image_path = "temp_image.jpg"
        video_path = "output_video.mp4"

        # ลบไฟล์เก่าทิ้ง (ถ้ามี) เพื่อป้องกันการเขียนทับผิดพลาด
        for file in [audio_path, image_path, video_path]:
            if os.path.exists(file):
                os.remove(file)

        # 3. สร้างเสียงพากย์ด้วย edge-tts
        print(f"Generating audio for text: {text}")
        subprocess.run(
            ['edge-tts', '--voice', 'th-TH-PremwadeeNeural', '--text', text, '--write-media', audio_path],
            check=True
        )

        # 4. ดาวน์โหลดรูปภาพจาก Pollinations.ai
        print(f"Downloading image from: {image_url}")
        img_response = requests.get(image_url)
        if img_response.status_code == 200:
            with open(image_path, 'wb') as f:
                f.write(img_response.content)
        else:
            return jsonify({"error": "Failed to download image"}), 400

        # 5. สร้างวิดีโอด้วย ffmpeg (ใส่ Ken Burns Effect ซูมเข้าช้าๆ สำหรับภาพแนวตั้ง)
        print("Generating video with ffmpeg...")
        ffmpeg_cmd = [
            'ffmpeg', '-y',
            '-loop', '1', # วนลูปภาพนิ่ง
            '-i', image_path, # ไฟล์ภาพ
            '-i', audio_path, # ไฟล์เสียง
            '-vf', "zoompan=z='min(zoom+0.0015,1.5)':d=700:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)',scale=720:1280", # เอฟเฟกต์ซูม
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-pix_fmt', 'yuv420p',
            '-shortest', # ตัดวิดีโอให้จบพร้อมเสียง
            video_path
        ]
        subprocess.run(ffmpeg_cmd, check=True)

        # 6. ส่งไฟล์วิดีโอกลับไปให้ n8n
        return send_file(video_path, mimetype='video/mp4', as_attachment=True, download_name='final_series.mp4')

    except subprocess.CalledProcessError as e:
        print("Command Execution Error:", e)
        return jsonify({"error": "System command failed", "details": str(e)}), 500
    except Exception as e:
        print("Application Error:", e)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # กำหนด Port สำหรับ Render
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
