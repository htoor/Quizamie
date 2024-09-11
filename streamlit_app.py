import streamlit as st
import openai
import csv
import json
import random
import os
from datetime import datetime

# Function to initialize OpenAI client
def get_llm():
    api_key = st.secrets['OPENAI_API_KEY']
    client = openai.OpenAI(api_key=api_key)
    return client

# Load existing problems
problem_db_file = "problem_database.json"
feedback_file = "feedback_data.csv"

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
            writer.writeheader()
        writer.writerow(data)

# Function to save a problem to the database
def save_problem_to_db(subject, difficulty, problem_data):
    if subject not in problem_database:
        problem_database[subject] = {}
    if difficulty not in problem_database[subject]:
        problem_database[subject][difficulty] = []
    problem_database[subject][difficulty].append(problem_data)
    with open(problem_db_file, "w") as file:
        json.dump(problem_database, file)

# Initialize LLM and session state
llm = get_llm()

# Reset session state (used for the "Cancel" functionality)
def reset_session_state():
    for key in ['step', 'module', 'difficulty', 'problem', 'correct_answer', 'solution', 'user_answer', 'used_problems', 'generate_clicked', 'check_answer_clicked']:
        if key in st.session_state:
            del st.session_state[key]
    st.session_state.step = 1


# Define the wizard steps
def step_1():
    st.title("Step 1: Choose a Module and Difficulty Level")
   
    with st.form("Problem Form"):
        subjects_k12 = ["English", "Math", "Science", "History", "Geography", "Art", "Music", "Physical Education"]
        st.session_state.module = st.selectbox("Choose a module:", subjects_k12, key="aModule")
        st.session_state.difficulty = st.selectbox("Select difficulty level:", ["Beginner", "Intermediate", "Advanced"], key="aDifficulty")
       
        # Enable the "Next" button only if both module and difficulty are selected
        next_button = st.form_submit_button("Generate", disabled=not (st.session_state.module and st.session_state.difficulty))
        cancel_button = st.form_submit_button("Cancel")
    print(next_button)
    if next_button:
        print("next button clicked")
        st.session_state.step = 2
        print("New state",st.session_state.step)
        st.rerun()
    if cancel_button:
        reset_session_state()


def step_2():
    st.title("Step 2: Solve a Problem")

    # Attempt to reuse a problem
    module = st.session_state.module
    difficulty = st.session_state.difficulty
    reusable_problems = [
        p for p in problem_database.get(module, {}).get(difficulty, [])
        if p["problem"] not in st.session_state["used_problems"]
    ]
   
    if reusable_problems:
        problem_data = random.choice(reusable_problems)
        print(problem_data)
        st.session_state["used_problems"].add(problem_data["problem"])
    else:
        prompt = (f"Generate a {difficulty.lower()} level {module} problem for a student to solve. "
                  "Provide the response as a JSON object with 'problem', 'answer', and 'solution'.")
        with st.spinner("Generating problem..."):
            problem_response = llm.chat.completions.create(
                messages=[{"role": "system", "content": prompt}],
                model="gpt-4o",
                max_tokens=500,
                n=1,
                stop=None,
                temperature=0.7,
            )
            problem = problem_response.choices[0].message.content.strip("```json").strip("```")
            problem_data = json.loads(problem)
            print(problem_data)
            save_problem_to_db(module, difficulty, problem_data)

    st.session_state.problem = problem_data["problem"]
    st.session_state.correct_answer = str(problem_data["answer"])
    st.session_state.solution = problem_data["solution"]

    #with st.form("Answer Form"):
    st.write("### Problem Statement:")
    st.write(st.session_state.problem)
    def set_answer():
        print("Answer set")
        st.session_state.user_answer =str(st.session_state.aUser_answer)
        st.session_state.step = 3
    st.session_state.user_answer = str(st.text_input("Enter your answer:", key="aUser_answer",on_change=set_answer))
    def check_answer():
        st.session_state.step = 3
        print("Check answer clicked",st.session_state.user_answer)

    next_button = st.button("Check Answer", on_click=check_answer)
    def back_button_clicked():
        st.session_state.step = 1
        print("Back button clicked",st.session_state.user_answer)

    #back_button = st.button("Back", on_click=back_button_clicked)
    cancel_button = st.button("Cancel")


    print("Did I press next button",next_button)
    if next_button:
        st.session_state.step = 3
        st.rerun()
        
    #if back_button:
    #    st.session_state.step = 1
    #    st.rerun()
    if cancel_button:
        reset_session_state()
        st.rerun()

def step_5():
    st.title("Step 3: Attempt the Problem")

    st.write("### Problem Statement:")
    st.write(st.session_state.problem)

    with st.form("Answer Form"):
        st.session_state.user_answer = st.text_input("Enter your answer:")
        submit_button = st.form_submit_button("Check Answer", disabled=not st.session_state.user_answer)
        back_button = st.form_submit_button("Back")
        cancel_button = st.form_submit_button("Cancel")
   
        if submit_button:
            st.session_state.check_answer_clicked = True
            st.session_state.step = 4
        if back_button:
            st.session_state.step = 1
        if cancel_button:
            reset_session_state()

def step_3():
    st.title("Step 3: Review Your Answer")

    correct_answer = st.session_state.correct_answer
    if st.session_state.user_answer.strip() == correct_answer.strip():
        st.success("Correct! Well done.")
    else:
        st.error(f"Incorrect. The correct answer is: {correct_answer}")
   
    with st.expander("View the solution"):
        st.write("### Step-by-Step Solution:")
        st.write(st.session_state.solution)

    st.write("### Was this feedback helpful?")

    # Thumbs-up and thumbs-down buttons
    col1, col2 = st.columns(2)
    with col1:
        thumbs_up = st.button("👍 Yes")
    with col2:
        thumbs_down = st.button("👎 No")
   
    # Capture feedback when either button is pressed
    if thumbs_up or thumbs_down:
        feedback_data = {
            "timestamp": datetime.now().isoformat(),
            "module": st.session_state.module,
            "question": st.session_state.problem,
            "difficulty": st.session_state.difficulty,
            "user_answer": st.session_state.user_answer,
            "correct_answer": st.session_state.correct_answer,
            "ai_solution": st.session_state.solution,
            "user_feedback": thumbs_up  # True if thumbs up, False if thumbs down
        }
        log_feedback(feedback_data)
        st.success("Thank you for your feedback!")

    done_button = st.button("Done")
    #back_button = st.button("Back")
   
    if done_button:
        reset_session_state()
        st.rerun()
    #if back_button:
    #    st.session_state.step = 2
    #    st.rerun()

# Render the correct step with navigation
if 'step' not in st.session_state:
    st.session_state.step = 1

if "used_problems" not in st.session_state:
    st.session_state["used_problems"] = set()

print(st.session_state.step)
if st.session_state.step == 1:
    #reset_session_state()
    step_1()
    print("step 1 complete")
    if st.session_state.step == 2:
        print("step 2")
        step_2()
        print("step 2 complete")
        
elif st.session_state.step == 2:
    print("step 2 inelif")
    step_2()
elif st.session_state.step == 3:
    step_3()
elif st.session_state.step == 4:
    step_4()