from flask import Flask, request, jsonify
import subprocess

app = Flask(__name__)

@app.route('/generate', methods=['POST'])
def generate_video():
    # 1. ดึงข้อมูล JSON อย่างถูกต้อง
    data = request.get_json()
    text = data.get('text')
    image_url = data.get('image_url')

    # เช็คว่ามีข้อความส่งมาจริงๆ เพื่อป้องกันค่า None
    if not text:
        return jsonify({"error": "Missing text parameter"}), 400

    # 2. กำหนดชื่อไฟล์เสียงล่วงหน้า (คาดว่าโค้ดเดิมอาจจะลืมประกาศตัวแปรนี้ หรือเผลอตั้งเป็น None)
    audio_path = "output_audio.mp3"

    # 3. รันคำสั่งสร้างเสียง
    subprocess.run(['edge-tts', '--voice', 'th-TH-PremwadeeNeural', '--text', text, '--write-media', audio_path], check=True)
    
    # ... (โค้ดส่วนโหลดภาพและตัดต่อวิดีโอด้วย ffmpeg) ...
    
    return jsonify({"status": "success"})
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
