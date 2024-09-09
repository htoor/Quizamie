import  streamlit as st
import openai
from openai import OpenAI
import csv
import json
import random
import os
 
from datetime import datetime
#from config import OPENAI_API_KEY
#from config import EMBEDDING_API_KEY
 
 
def get_llm():
   
   # Initialize OpenAI client with API key
    api_key = st.secrets['OPENAI_API_KEY']
    client = OpenAI(api_key=api_key)

   
    return client
 
 
# Set up OpenAI API key
# File paths to store problems and feedback data
problem_db_file = "problem_database.json"
# File path to store feedback data
feedback_file = "feedback_data.csv"
# Load existing problems
if os.path.exists(problem_db_file):
    with open(problem_db_file, "r") as file:
        problem_database = json.load(file)
else:
    problem_database = {}
 
# Function to log feedback data
def log_feedback(data):
    file_exists = os.path.isfile(feedback_file)
    with open(feedback_file, mode='a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=data.keys())
        if not file_exists:
            writer.writeheader()  # Write header if file doesn't exist
        writer.writerow(data)
llm=get_llm()
# Function to save problem to the database
def save_problem_to_db(subject, difficulty, problem_data):
    if subject not in problem_database:
        problem_database[subject] = {}
    if difficulty not in problem_database[subject]:
        problem_database[subject][difficulty] = []
   
    problem_database[subject][difficulty].append(problem_data)
   
    with open(problem_db_file, "w") as file:
        json.dump(problem_database, file)
 
 
# Streamlit UI
st.title("Learning Platform")
st.write("Select a module and ask a question!")
 
# Add a dropdown to select the module
module = st.selectbox("Choose a module:", [ "Math","General"])
 
# Add a dropdown for difficulty level if Math module is selected if module == "Math":
difficulty = st.selectbox("Select difficulty level:", ["Beginner", "Intermediate", "Advanced"])
 
if module == "Math":
    # Track problems used in the current session
    if "used_problems" not in st.session_state:
        st.session_state["used_problems"] = set()
   
    # Attempt to reuse a problem
    reusable_problems = [
        p for p in problem_database.get(module, {}).get(difficulty, [])
        if p["problem"] not in st.session_state["used_problems"]
    ]
 
    if reusable_problems:
        problem_data = random.choice(reusable_problems)
        st.session_state["used_problems"].add(problem_data["problem"])
    else:
        problem_data = None
 
    # Ensure at least one new problem is generated
    if not problem_data or len(st.session_state["used_problems"]) < 1:
        if st.button("Generate Problem"):
            # Generate a math problem based on the selected difficulty level
            prompt = (f"Generate a {difficulty.lower()} level math problem for a student to solve. "
                "Provide the response as a JSON object with keys: 'problem', 'answer', and 'solution'."
)
            with st.spinner("Generating problem..."):
                problem_response = llm.chat.completions.create(messages=[{"role": "system", "content":prompt}],
                    model="gpt-4o",
                    max_tokens=100,
                    n=1,
                    stop=None,
                    temperature=0.7,
                )
               
                problem = problem_response.choices[0].message.content
                print(problem)
                problem_data = eval(problem)
                st.session_state["used_problems"].add(problem_data["problem"])
                save_problem_to_db(module, difficulty, problem_data)
   
        # Display the problem statement
    if problem_data:
        st.write("### Problem Statement:")
        st.write(problem_data['problem'])
       
        # Allow user to attempt the problem
        user_answer = st.text_input("Enter your answer:")
 
        if user_answer:
            correct_answer = problem_data["answer"]
            if user_answer.strip() == correct_answer.strip():
                st.success("Correct! Well done.")
            else:
                st.error(f"Incorrect. The correct answer is: {correct_answer}")
           
            # Provide an option to view the solution
            with st.expander("View the solution"):
                st.write("### Step-by-Step Solution:")
                st.write(problem_data["solution"])
           
            
            # Capture feedback
            feedback_choice = st.radio("Did you find this feedback helpful?", ["👍", "👎"], key="feedback_choice")
           
            if feedback_choice:
                feedback_data = {
                    "timestamp": datetime.now().isoformat(),
                    "question": problem_data["problem"],
                    "difficulty": difficulty,
                    "user_answer": user_answer,
                    "correct_answer": correct_answer,
                    "ai_solution": problem_data["solution"],
                    "user_feedback": (feedback_choice=="👍")
                }
                log_feedback(feedback_data)
               
                # Update problem database with feedback
                for problem in problem_database[module][difficulty]:
                    if problem["problem"] == problem_data["problem"]:
                        problem["feedback"] = feedback_choice
                        break
                with open(problem_db_file, "w") as file:
                    json.dump(problem_database, file)
               
                st.success("Thank you for your feedback!")
 
else:
    user_input = st.text_input("Ask a question or enter a topic:")
 
    if user_input:
        # Generate AI response using OpenAI's GPT
        with st.spinner("Generating response..."):
            if (True):
                response = llm.chat.completions.create(messages=[{"role": "system", "content":user_input}],
                        model="gpt-4o",
                        max_tokens=150,
                        n=1,
                        stop=None,
                        temperature=0.7,
                    )
                st.write("### AI Response:")
                st.write(response.choices[0].text.strip())
            else:
                st.write("### AI Response:")
                st.write(user_input.strip())

 