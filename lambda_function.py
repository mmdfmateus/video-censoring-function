import json
import os
import subprocess
import shlex
from venv import logger
import boto3
import urllib3
from secrets import token_bytes

S3_DESTINATION_BUCKET = "ugcvideo-destination-bucket"
SIGNED_URL_TIMEOUT = 6000
FFMPEG_STATIC = "/tmp/ffmpeg"
TMP_DESTINATION = "/tmp/"

POSTBACK_ENDPOINT = "https://webhook-test.com/6ed5af50a45fc480bb0f4b2f9b2cad90"


def generate_file_name(bytes=32):
  """Generates a random filename in hexadecimal format.

  Args:
      bytes: The number of bytes to use for generating randomness. Defaults to 32.

  Returns:
      A string containing the random filename in hexadecimal format.
  """
  random = token_bytes(bytes)
  return random.hex()

os.system("cp -ra ./ffmpeg /tmp/")
os.system("cp -ra ./brfutsal.png /tmp/")
os.system("chmod -R 775 /tmp")

class PostBackRequest(object):
    videoId = 0
    isError = False
    censoredFileName = ""

    # The class "constructor" - It's actually an initializer 
    def __init__(self, videoId, isError, censoredFileName):
        self.videoId = videoId
        self.isError = isError
        self.censoredFileName = censoredFileName

    def to_json(self):
        return {
            "videoId": self.videoId,
            "isError": self.isError,
            "censoredFileName": self.censoredFileName
        }

http = urllib3.PoolManager()

def lambda_handler(event, context):
    videoId = ""
    isError = False
    censoredFileName = ""
    postbackUrl = ""

    try:
        s3_source_bucket = event['Records'][0]['s3']['bucket']['name']
        s3_source_key = event['Records'][0]['s3']['object']['key']

        s3_client = boto3.client('s3')
        s3_source_signed_url = s3_client.generate_presigned_url('get_object',
            Params={'Bucket': s3_source_bucket, 'Key': s3_source_key},
            ExpiresIn=SIGNED_URL_TIMEOUT)
            
        object_head = s3_client.head_object(Bucket=s3_source_bucket, Key=s3_source_key)

        videoId = object_head['Metadata']['videoid']
        postbackUrl = object_head['Metadata']['postbackurl']

        cmd = "ls -la /tmp"
        returned_output = subprocess.check_output(cmd.split())
        result = returned_output.decode("utf-8")
        print("Resultado ls /tmp:", result)

        # ffmpeg -i video.mp4 -i brfutsal.png -filter_complex "[1]format=rgba,colorchannelmixer=aa=0.4[logo];[logo][0]scale2ref=oh*mdar:ih*0.5[logo][video];[video][logo]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2" out_video.mp4
        
        censoredFileName = generate_file_name()
        complete_destination = TMP_DESTINATION + censoredFileName + ".mp4"

        print('starting to run ffmpeg command')
        # ffmpeg_cmd = FFMPEG_STATIC + " -i \"" + s3_source_signed_url + "\" -f mpegts -c:v copy -af aresample=async=1:first_pts=0 -"
        ffmpeg_cmd = FFMPEG_STATIC + " -y -i \"" + s3_source_signed_url + "\" -i /tmp/brfutsal.png -filter_complex \"[1]format=rgba,colorchannelmixer=aa=0.4[logo];[logo][0]scale2ref=oh*mdar:ih*0.5[logo][video];[video][logo]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2\" " + complete_destination
        print("full command: ", ffmpeg_cmd)
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

        s3 = boto3.resource('s3')
        bucket = s3.Bucket(S3_DESTINATION_BUCKET)
        bucket.upload_file(complete_destination, censoredFileName)
    
    except Exception as err:
        isError = True
        print('An error occurred: %s', repr(err))
        logger.exception(err)

    finally:
        request = PostBackRequest(videoId, isError, censoredFileName)
        encoded_body = json.dumps(request.to_json())
        r = http.request('POST', postbackUrl or POSTBACK_ENDPOINT, headers={'Content-Type': 'application/json'}, body=encoded_body)

        return {
            'statusCode': 200,
            'body': json.dumps('Processing complete successfully')
        }