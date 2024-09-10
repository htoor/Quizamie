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
# Check if session state is None and set it to "Generate Problem"
# Initialize session state variables
if 'generate_clicked' not in st.session_state:
    st.session_state.generate_clicked = False
if 'check_answer_clicked' not in st.session_state:
    st.session_state.check_answer_clicked = False
# Track problems used in the current session
if "used_problems" not in st.session_state:
    st.session_state["used_problems"] = set()
# Add a dropdown to select the module
with st.form("Problem Form"):
    subjects_k12 = ["English", "Math", "Science", "History", "Geography", "Art", "Music", "Physical Education"]
    module = st.selectbox("Choose a module:", subjects_k12)
    # Add a dropdown for subjects if General module is selected
    difficulty = st.selectbox("Select difficulty level:", ["Beginner", "Intermediate", "Advanced"])
    # Ensure at least one new problem is generated
    if st.form_submit_button("Generate Problem"):
        st.session_state.generate_clicked = True
        st.session_state.module = module
        st.session_state.difficulty = difficulty

if st.session_state.generate_clicked:    
    # Attempt to reuse a problem
    reusable_problems = [
        p for p in problem_database.get(module, {}).get(difficulty, [])
        if p["problem"] not in st.session_state["used_problems"]
]
    if reusable_problems:
        problem_data = random.choice(reusable_problems)
        st.session_state["used_problems"].add(problem_data["problem"])
    else:
        prompt = (f"Generate a {difficulty.lower()} level {module} problem for a student to solve. "
            "Provide the response as a simple JSON object with keys: 'problem', 'answer', and 'solution'. Make sure that the generated json string can be parsed as a json object and errror out due to special characters"
        )
        with st.spinner("Generating problem..."):
            problem_response = llm.chat.completions.create(messages=[{"role": "system", "content":prompt}],
                model="gpt-4o",
                max_tokens=500,
                n=1,
                stop=None,
                temperature=0.7,
            )
            
            problem = problem_response.choices[0].message.content
            # Remove the three ticks and the word "json" from the first line
            problem = problem.replace("```json", "").replace("```", "").replace("json", "", 1)
            print(problem)
            problem_data = json.loads(problem)
            st.session_state.problem = problem_data["problem"]
            print(problem_data)
            #st.session_state["used_problems"].st.session_state.problem)
            save_problem_to_db(module, difficulty, problem_data)
        reusable_problems = [
            p for p in problem_database.get(module, {}).get(difficulty, [])
            if p["problem"] not in st.session_state["used_problems"]
        ]
        

    # Display the problem statement
    if problem_data:
        st.session_state.correct_answer=problem_data["answer"]
        st.session_state.solution=problem_data["solution"]
        st.write("### Problem Statement:")
        st.write(problem_data['problem'])
        
    # Allow user to attempt the problem
    with st.form("Answer Form"):
        st.session_state.user_answer = st.text_input("Enter your answer:")
        submit_button = st.form_submit_button("Check Answer")

        if submit_button:
            st.session_state.check_answer_clicked = True
        if st.session_state.check_answer_clicked:   
            correct_answer = st.session_state.correct_answer

            if st.session_state.user_answer .strip() == correct_answer.strip():
                st.success("Correct! Well done.")
            else:
                st.error(f"Incorrect. The correct answer is: {correct_answer}")
            
            # Provide an option to view the solution
            with st.expander("View the solution"):
                st.write("### Step-by-Step Solution:")
                st.write(st.session_state.solution)
            
            
            # Capture feedback
            feedback_choice = st.radio("Did you find this feedback helpful?", ["👍", "👎"], key="feedback_choice")
            
            if feedback_choice:
                feedback_data = {
                    "timestamp": datetime.now().isoformat(),
                    "module":st.session_state.module,
                    "question": st.session_state.problem,
                    "difficulty": st.session_state.difficulty,
                    "user_answer": st.session_state.user_answer ,
                    "correct_answer": st.session_state.correct_answer,
                    "ai_solution": st.session_state.solution,
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

    