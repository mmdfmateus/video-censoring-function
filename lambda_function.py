import json
import os
import subprocess
import shlex
import boto3

S3_DESTINATION_BUCKET = "ugcvideo-destination-bucket"
SIGNED_URL_TIMEOUT = 6000
FFMPEG_STATIC = "/tmp/ffmpeg"
TMP_DESTINATION = "/tmp/"

os.system("cp -ra ./ffmpeg /tmp/")
os.system("cp -ra ./brfutsal.png /tmp/")
os.system("chmod -R 775 /tmp")

def lambda_handler(event, context):

    s3_source_bucket = event['Records'][0]['s3']['bucket']['name']
    s3_source_key = event['Records'][0]['s3']['object']['key']

    s3_source_basename = os.path.splitext(os.path.basename(s3_source_key))[0]
    s3_destination_filename = s3_source_basename + "_censored.mp4"

    s3_client = boto3.client('s3')
    s3_source_signed_url = s3_client.generate_presigned_url('get_object',
        Params={'Bucket': s3_source_bucket, 'Key': s3_source_key},
        ExpiresIn=SIGNED_URL_TIMEOUT)
        
    cmd = "ls -la /tmp"
    returned_output = subprocess.check_output(cmd.split())
    result = returned_output.decode("utf-8")
    print("Resultado ls /tmp:", result)

    # ffmpeg_cmd = "/opt/ffmpeg -i \"" + s3_source_signed_url + "\" -f mpegts -c:v copy -af aresample=async=1:first_pts=0 -"
    # command1 = shlex.split(ffmpeg_cmd)
    # p1 = subprocess.run(command1, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # ffmpeg -i video.mp4 -i brfutsal.png -filter_complex "[1]format=rgba,colorchannelmixer=aa=0.4[logo];[logo][0]scale2ref=oh*mdar:ih*0.5[logo][video];[video][logo]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2" out_video.mp4
    
    complete_destination = TMP_DESTINATION + s3_destination_filename

    print('starting to run ffmpeg command')
    # ffmpeg_cmd = FFMPEG_STATIC + " -i \"" + s3_source_signed_url + "\" -f mpegts -c:v copy -af aresample=async=1:first_pts=0 -"
    ffmpeg_cmd = FFMPEG_STATIC + " -y -i \"" + s3_source_signed_url + "\" -i /tmp/brfutsal.png -filter_complex \"[1]format=rgba,colorchannelmixer=aa=0.4[logo];[logo][0]scale2ref=oh*mdar:ih*0.5[logo][video];[video][logo]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2\" " + complete_destination
    print("full command: ", ffmpeg_cmd)
    # command1 = shlex.split(ffmpeg_cmd)
    p1 = subprocess.run(ffmpeg_cmd, shell=True)
    print("Resultado do comando:", p1)

    # print pwd to see output file
    cmd = "ls -la"
    returned_output = subprocess.check_output(cmd.split())
    result = returned_output.decode("utf-8")
    print("Resultado ls:", result)

    # copy output to /tmp
    # cmd = "cp -ra ./" + s3_destination_filename + " /tmp/"
    # returned_output = subprocess.check_output(cmd.split())
    # result = returned_output.decode("utf-8")
    # print("Resultado cp:", result)

    cmd = "ls -la /tmp"
    returned_output = subprocess.check_output(cmd.split())
    result = returned_output.decode("utf-8")
    print("Resultado ls /tmp:", result)

    # resp = s3_client.put_object(Body=complete_destination, Bucket=S3_DESTINATION_BUCKET, Key=s3_destination_filename)

    s3 = boto3.resource('s3')
    bucket = s3.Bucket(S3_DESTINATION_BUCKET)
    bucket.upload_file(complete_destination, s3_destination_filename)

    return {
        'statusCode': 200,
        'body': json.dumps('Processing complete successfully')
    }