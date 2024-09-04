@app.route("/chat", methods=['GET', 'POST'])
def chat():
    if request.method == 'POST':
        user_prompt = request.json.get('prompt')

        session_history = session.get('chat_history', [])
        llm_chatbot = LLMChatbot()
        llm_chatbot.session_history.messages = session_history

        response = llm_chatbot.generate_response(user_prompt)

        session['chat_history'] = llm_chatbot.session_history.messages

        return jsonify({'response': response})
    return render_template("chat.html")