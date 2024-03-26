"""
郭泽斌于2023.04.29参照app.py创建，用于连接github开源项目 Fay 数字人
"""

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
import sys

video_list = []
audio_paths = []
fay_ws = None
video_cache = {}
# 定义全局变量作为停止信号
stop_thread = False

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
        # 在独立的线程中运行 run_forever
        thread = threading.Thread(target=lambda: fay_ws.run_forever())
        thread.start()

        try:
            while thread.is_alive():  # 检查WebSocket线程是否仍在运行
                thread.join(timeout=1)  # 每秒检查一次
                if stop_thread:  # 如果收到停止信号
                    fay_ws.close()  # 关闭WebSocket连接
                    break
        except KeyboardInterrupt:
            fay_ws.close()

    def reconnect():
        if not stop_thread:
            global fay_ws
            fay_ws = None
            time.sleep(5)  # 等待一段时间后重连
            connect()

    connect()

def convert_mp3_to_wav(input_file, output_file):
    audio = AudioSegment.from_mp3(input_file)
    audio.export(output_file, format='wav')


def play_video():
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
                if len(imgs) > 0:
                    frame = imgs[0]
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    cv2.imshow('Granden-2d', frame)
                    # 等待 38 毫秒
                    cv2.waitKey(38)
                    i = i - 1
                elif i == 0:
                    break
        else:
            cv2.imshow('Granden-2d', frame)
            # 等待 38 毫秒
            cv2.waitKey(38)

# def play_video():
#     global video_list
#     default_video_path = "data/pretrained/train.mp4"  # 默认视频的路径

#     while True:
#         print("video_list:",video_list)
#         if len(video_list) > 0:
#             # 从列表中取出一个视频对象
#             videoObj = video_list.pop(0)
#             video_path = videoObj['video']
#         else:
#             # 没有更多视频时播放默认视频
#             video_path = default_video_path
#         print("video_path:",video_path)
#         cap = cv2.VideoCapture(video_path)

#         # 循环直到视频结束
#         while cap.isOpened():
#             # 读取视频帧
#             ret, frame = cap.read()
#             if not ret:
#                 # print("Can't receive frame (stream end?). Exiting ...")
#                 break
#             cv2.imshow('frame', frame)
#             #等待38毫秒後,按下ESC键或窗口被关闭而退出循环
#             key = cv2.waitKey(38)
#             if key == 27 or cv2.getWindowProperty('frame', cv2.WND_PROP_VISIBLE) < 1:
#                 cap.release()
#                 stop_fay_thread()
#                 sys.exit()


def play_audio(audio_file):
    pygame.mixer.init()
    pygame.mixer.music.load(audio_file)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)
    pygame.mixer.music.stop()

def start_fay_thread():
    global stop_thread
    stop_thread = False  # 重置停止信号
    threading.Thread(target=connet_fay).start()

def stop_fay_thread():
    global stop_thread
    stop_thread = True  # 设置停止信号以停止线程

if __name__ == '__main__':

    audio_pre_process()
    video_pre_process()
    start_fay_thread()
    play_video()


    
    

