from flask import Flask, request, send_file
import subprocess
import requests
import uuid
import os

app = Flask(__name__)

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    image_url = data.get('image_url')
    text = data.get('thai_text')

    uid = str(uuid.uuid4())
    img_path = f"/tmp/{uid}.jpg"
    audio_path = f"/tmp/{uid}.mp3"
    out_path = f"/tmp/{uid}.mp4"

    try:
        # 1. โหลดรูปภาพ
        with open(img_path, 'wb') as f:
            f.write(requests.get(image_url).content)

        # 2. สร้างเสียงพากย์ด้วย Edge-TTS
        subprocess.run(['edge-tts', '--voice', 'th-TH-PremwadeeNeural', '--text', text, '--write-media', audio_path], check=True)

        # 3. ตัดต่อวิดีโอ (Ken Burns) ด้วย FFmpeg
        subprocess.run([
            'ffmpeg', '-y', '-loop', '1', '-i', img_path, '-i', audio_path,
            '-vf', "zoompan=z='min(zoom+0.001,1.1)':d=250:s=720x1280",
            '-c:v', 'libx264', '-tune', 'stillimage', '-c:a', 'aac', '-b:a', '192k',
            '-pix_fmt', 'yuv420p', '-shortest', out_path
        ], check=True)

        # ส่งไฟล์วิดีโอกลับไปให้ n8n
        return send_file(out_path, mimetype='video/mp4')

    finally:
        # เคลียร์ไฟล์ขยะ
        for f in [img_path, audio_path]:
            if os.path.exists(f):
                os.remove(f)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
