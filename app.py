# app.py
import os
import json
from flask import Flask, request, jsonify
from slack import WebClient
from slack.errors import SlackApiError
from slackeventsapi import SlackEventAdapter
app = Flask(__name__)

client = WebClient(token=os.environ['SLACK_API_TOKEN'])
slack_events_adapter = SlackEventAdapter(
    os.environ['SLACK_SIGNING_SECRET'], "/event/", app)

@app.route("/")
def hello():
  return "Hello there!"


@app.route('/post/', methods=['POST'])
def post_something():
    """ Respond to /task command issues by Slack User
    - Parse the task message
    - Send messaged to assigned user about the task
    """

    if '/task' == request.form.get("command"):
        text = request.form.get("text")
        assiginee_id, task = _parse_task_msg(text)
        user_id = request.form.get('user_id')

    if task:
        response = client.chat_postMessage(
            channel=assiginee_id,
            blocks=_build_add_task_message(task, user_id))
        print(response)
        # assert response["message"]["text"] == "Hello world!"
        return f'<{assiginee_id}> has been assigned the task "{task}"'
    else:
        return "Please make sure you formatted your message correctly!"


def _parse_task_msg(text):
    """ Parse the task message and return the User ID and task """
    start_pos = text.find("<")
    end_pos = text.find(">")

    assiginee_id = text[start_pos:end_pos +
                                        1].strip('<>')
    if "|" in assiginee_id:
        assiginee_id, _ = assiginee_id.split('|')

    task = text[end_pos + 1:].strip()

    return assiginee_id, task

def _build_add_task_message(task, user_id):
    block = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"<@{user_id}> has assigned you the following task:"
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": task
            }
        },
        {
            "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Complete",
                            "emoji": True
                        },
                        "style": "primary",
                        "value": "complete"
                    }
               ]
        }
    ]

    return block


def _build_task_completed_message(task, assiginer_id):
    # assiginer_id = assiginer_id.strip('@')
    block = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"Congratulations! You completed the task '{task}' assigned by <@{assiginer_id.strip('@')}>"
            }
        }
    ]

    return block

@app.route('/interactive_endpoint/', methods=['POST'])
def interactive_endpoint():
    """ Respond to task complete action from assigned user!
    1. Tell the assigner that task has been completed.
    2. Update the message to assignee to let them know that
    task has been completed. Remoe the Complete button.
    """
    params = json.loads(request.form.get('payload'))
    # print(params['message']['blocks'][0]['text']['text'])
    assiginer_id, _ = _parse_task_msg(
        params['message']['blocks'][0]['text']['text'])
    task = params['message']['blocks'][1]['text']['text']
    assigned_id = params['user']['id']

    actions = params['actions']
    if actions[0]['value'] == 'complete':
        # Send messaged to original task assigner
        client.chat_postMessage(
            channel=assiginer_id,
            text=f"<@{assigned_id}> has completed the task: {task}!"
        )

        # Update message to remove the comnplete button action
        client.chat_update(
            channel=params['container']['channel_id'],
            ts=params['container']['message_ts'],
            blocks=_build_task_completed_message(task, assiginer_id)
        )
        return "Worked"
    else:
        return "Didn't Work"

@app.route('/event/', methods=['POST'])
def event_handler():
    """ Respond to challenge ping from Slack """
    body = request.get_json()
    if 'challenge' in body:
        challenge = body['challenge']
        return jsonify({
            "challenge": challenge,
        })
    else:
        return jsonify({
            "ERROR": "no challenge found, please send a name."
        })


# A welcome message to test our server
@app.route('/')
def index():
    return "<h1>Welcome to our server !!</h1>"


if __name__ == '__main__':
    app.run(threaded=True, port=5000)
