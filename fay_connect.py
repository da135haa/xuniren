import base64
import time
import json
import gevent
from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler
from tools import audio_pre_process, video_pre_process, generate_video, audio_process
import os
import re
import numpy as np
import threading
import websocket
from pydub import AudioSegment
from moviepy.editor import VideoFileClip, AudioFileClip, concatenate_videoclips
import cv2
import pygame
import hashlib
import video_stream
import queue
from datetime import datetime, timedelta
import sched

running = True
video_list = []
audio_paths = []
fay_ws = None
video_cache = {}
task_queue = queue.Queue()

def worker():
    while running:
        try:
            # 尝试从队列中获取任务，等待最多1秒
            task = task_queue.get(timeout=1)
        except queue.Empty:
            # 如果队列为空，则跳过此次循环
            continue

        # 解包任务参数，并执行任务
        message_dict = task
        global video_list
        global video_cache
        aud_dir = message_dict["Data"]["Value"]
        aud_dir = aud_dir.replace("\\", "/")
        print('message:', aud_dir, type(aud_dir))
        basedir = ""
        for i in aud_dir.split("/"):
            basedir = os.path.join(basedir,i)
        basedir = basedir.replace(":",":\\")   
        num = time.time()
        new_path = r'./data/audio/aud_%d.wav'%num  #新路径                
        old_path = basedir                

        convert_mp3_to_wav(old_path, new_path) 
        audio_hash = hash_file_md5(new_path)
        audio_paths.append(new_path)
        # if audio_hash in video_cache:
        #     video_list.append({"video": video_cache[audio_hash], "audio": new_path})
        #     ret, frame = cap.read()

        #     print("视频已存在，直接播放。")
        # else:
        audio_path = 'data/audio/aud_%d.wav' % num
        audio_process(audio_path)
        audio_path_eo = 'data/audio/aud_%d_eo.npy' % num
        video_path = 'data/video/results/ngp_%d.mp4' % num
        output_path = 'data/video/results/output_%d.mp4' % num

        generate_video(audio_path, audio_path_eo, video_path, output_path)
        video_list.append({"video" : output_path, "audio" : new_path})
        video_cache[audio_hash] = output_path
        # 标记任务完成
        task_queue.task_done()

#增加MD5音频标记，避免重复生成视频
def hash_file_md5(filepath):
    md5 = hashlib.md5()
    with open(filepath, 'rb') as f:
        while True:
            data = f.read(65536)  # Read in 64kb chunks
            if not data:
                break
            md5.update(data)
    return md5.hexdigest()


def connet_fay():
    global video_list
    global video_cache
    global fay_ws
    global audio_paths

    def on_message(ws, message):
        if "audio" in message:
            message_dict = json.loads(message)
            task_queue.put((message_dict))




    def on_error(ws, error):
        print(f"Fay Error: {error}")
        reconnect()

    def on_close(ws):
        print("Fay Connection closed")
        reconnect()

    def on_open(ws):
        print("Fay Connection opened")

    def connect():
        global fay_ws
        ws_url = "ws://127.0.0.1:10002"
        fay_ws = websocket.WebSocketApp(ws_url,
                                        on_message=on_message,
                                        on_error=on_error,
                                        on_close=on_close)
        fay_ws.on_open = on_open
        fay_ws.run_forever()

    def reconnect():
        if running:
            global fay_ws
            fay_ws = None
            time.sleep(5)  # 等待一段时间后重连
            connect()

    connect()

def convert_mp3_to_wav(input_file, output_file):
    audio = AudioSegment.from_mp3(input_file)
    audio.export(output_file, format='wav')


def play_video():
    global running
    global video_list
    global audio_paths
    audio_path = None
    frame = None
    _, frame = cv2.VideoCapture("data/pretrained/train.mp4").read()
    while True:
        if video_stream.get_idle() > int(video_stream.get_video_len() / 3):
            if len(audio_paths)>0:
                audio_path = audio_paths.pop(0)
                print(audio_path)
                threading.Thread(target=play_audio, args=[audio_path]).start()  # play audio
            i = video_stream.get_video_len()
            video_stream.set_video_len(0)
            #循环播放视频帧
            while True:
                imgs = video_stream.read()
                if len(imgs) > 0: # type: ignore
                    frame = imgs[0]
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    cv2.imshow('2d', frame)
                    # 等待 38 毫秒
                    cv2.waitKey(38)
                    i = i - 1
                elif i == 0:
                    break
        else:
            cv2.imshow('2d', frame)
            #等待38毫秒後,按下ESC键或窗口被关闭而退出循环
            key = cv2.waitKey(38)
            if key == 27 or cv2.getWindowProperty('2d', cv2.WND_PROP_VISIBLE) < 1:
                running = False  # 设置 running 为 False，通知线程停止
                cv2.destroyAllWindows()
                fay_ws.close()
                return

def play_audio(audio_file):
    pygame.mixer.init()
    pygame.mixer.music.load(audio_file)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)
    pygame.mixer.music.stop()

def delete_old_files(directory):
    print("觸發刪除任務:",directory)
    """删除指定目录下创建时间超过10分钟的文件"""
    now = datetime.now()
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        if os.path.isfile(file_path):
            file_stat = os.stat(file_path)
            creation_time = datetime.fromtimestamp(file_stat.st_ctime)
            if now - creation_time > timedelta(minutes=10):
                print(f"Deleting {file_path}...")
                os.remove(file_path)

def scheduled_deletion(directories, scheduler, interval=600):
    """安排定期删除任务，适用于多个目录"""
    for directory in directories:
        delete_old_files(directory)  
    # 再次安排该任务，形成循环
    scheduler.enter(interval, 1, scheduled_deletion, (directories, scheduler, interval))
                
if __name__ == '__main__':
    #定時刪除產生的數據
    # 启动定时任务（例如，每600秒（10分钟）运行一次）
    s = sched.scheduler(time.time, time.sleep)
    directories_to_clean = [
        "data/audio",
        "data/video/results",
    # 添加更多目录路径...
    ]
    s.enter(0, 1, scheduled_deletion, (directories_to_clean, s, 600))
    s.run()

    audio_pre_process()
    video_pre_process()
    video_stream.start()
    threading.Thread(target=connet_fay, args=[]).start()
    threading.Thread(target=worker, daemon=True).start()
    play_video()