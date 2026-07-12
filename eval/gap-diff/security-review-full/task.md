# Security review

Review this Flask password-reset flow. Find every real vulnerability with a concrete exploit path.

```python
import time, hashlib
reset_tokens = {}   # token -> email

@app.route('/forgot', methods=['POST'])
def forgot():
    email = request.json['email']
    user = db.users.find_one({'email': email})
    if not user:
        return {'error': 'no account with that email'}, 404
    token = hashlib.md5((email + str(time.time())).encode()).hexdigest()
    reset_tokens[token] = email
    send_email(email, f"Reset here: https://app.com/reset?token={token}")
    return {'ok': True}

@app.route('/reset', methods=['POST'])
def reset():
    token = request.json['token']
    new_password = request.json['new_password']
    email = reset_tokens.get(token)
    if not email:
        return {'error': 'invalid token'}, 400
    db.users.update_one({'email': email}, {'$set': {'password': new_password}})
    return {'ok': True}
```
