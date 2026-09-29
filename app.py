import os
import subprocess
import requests
from flask import Flask, request, jsonify, send_file
from gtts import gTTS
import imageio_ffmpeg
import replicate

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
        silent_video_path = "temp_silent.mp4"
        final_video_path = "output_video.mp4"

        for file in [audio_path, silent_video_path, final_video_path]:
            if os.path.exists(file):
                os.remove(file)

        # 1. สร้างเสียงพากย์
        print("1. Generating audio with gTTS...")
        tts = gTTS(text=text, lang='th')
        tts.save(audio_path)

        # 2. ส่งภาพนิ่งไปทำวิดีโอขยับได้ด้วย Replicate (ใช้โมเดล Stable Video Diffusion)
        print("2. Generating AI Video via Replicate... (Please wait 1-2 minutes)")
        output = replicate.run(
            "stability-ai/stable-video-diffusion:3f0457e4619daac51203dedb472816fd4af51f3149fa7a9e0b5ffcf1b8172438",
            input={"input_image": image_url, "sizing_strategy": "maintain_aspect_ratio"}
        )
        
        # ดึง URL ของไฟล์วิดีโอที่ Replicate สร้างเสร็จแล้ว
        video_url = output if isinstance(output, str) else output[0]
        
        print("Downloading silent video...")
        vid_response = requests.get(video_url)
        with open(silent_video_path, 'wb') as f:
            f.write(vid_response.content)

        # 3. รวมวิดีโอและเสียงเข้าด้วยกัน (ใช้คำสั่ง -stream_loop -1 เพื่อให้ภาพวนลูปจนจบเสียงพากย์)
        print("3. Combining Audio and Video...")
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        ffmpeg_cmd = [
            ffmpeg_exe, '-y',
            '-stream_loop', '-1',  # สั่งให้วิดีโอวนลูป
            '-i', silent_video_path,
            '-i', audio_path,
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-pix_fmt', 'yuv420p',
            '-shortest', # ตัดจบเมื่อเสียงพากย์สิ้นสุด
            final_video_path
        ]
        
        subprocess.run(ffmpeg_cmd, check=True, capture_output=True, text=True)

        print("Done! Sending video back to n8n.")
        return send_file(final_video_path, mimetype='video/mp4', as_attachment=True, download_name='final_animated_series.mp4')

    except Exception as e:
        print("Error:", e)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
