import pandas as pd
import pickle
import numpy as np
import os
from openai import OpenAI

client = OpenAI(base_url="https://api.groq.com/openai/v1",
                api_key=os.environ.get("GROQ_API_KEY"))


def explain_prediction(probability, input_dict, surname):

    prompt = f'''You are an expert data scientist at a bank, where you specialize in interpreting and explaining predictions of machine learning models

    Your machine learning model has predicted that a customer named {surname} has a {round(probability * 100, 1)}% probability of churning, based on the information provided below.

    Here is the customers information:
    {input_dict}

    Here are the machine learning model's top 10 most important features for predicting churn:

                Feature | Importance
   ------------------------------------------------
         SumOfProducts  | 0.3238888
        isActiveMember  | 0.1641460
                   Age  | 0.1095500
     Geography_Germany  | 0.0913730
               Balance  | 0.0527860
      Geography_France  | 0.0464630
         Gender_Female  | 0.0452830
       Geography_Spain  | 0.0368550
           CreditScore  | 0.0350050
        EstimatedSalary | 0.0326550
              HasCrCard | 0.0319400
                 Tenure | 0.0300540
            Gender_Male | 0.0080000

      {pd.set_option('display.max_columns', None)}

      Here are summary statistics for churned customers:
      {df[df['Exited'] == 1].describe()}

        Here are summary statistics for non-churned customers:
        {df[df['Exited'] == 0].describe()}

      - If the customer has over a 40% risk of churning, generate a 3 sentence explanation of why they're at risk of churning.
      - If the customer has less than a 40% risk of churning, generate a 3 sentence explanation of why they might not be at risk of churning.
      - Your explanation should be based on the customer's information, the summary statistics of churned and non-churned customers, and the feature importances provided.

      Don't mention the probability of churning, or the machine learning model, or say anything like "Based on the machine learning model's prediction and top 10 most important features", just explain the prediction.
      
    '''

    print("EXPLANATION PROMPT", prompt)

    raw_response = client.chat.completions.create(
        model='llama-3.2-3b-preview',
        messages=[{
            "role": "user",
            "content": prompt
        }],
    )
    return raw_response.choices[0].message.content

def generate_email(probability, input_dict, explanation, surname):
    prompt = f'''You are a manager at HS Bank. You are responsible for ensuring customers stay with the bank and are incentivized with various offers.
    
    You noticed a customer named {surname} has a {round(probability * 100, 1)}% probability of churning.

    Here is the customer's information:
    {input_dict}

    Here is some explanation as to why the customer might be at risk of churning:
    {explanation}

    Generate an email to the customer based on their information, asking them to stay if they are at risk of churning, or offering them incentives so that they become more loyal to the bank.

    Make sure to list out a set of incentives to stay based on their information, in bullet point format. Don't ever mention the probability of churning, or the machine learning model to the customer. 
    
    '''
    raw_response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages = [{
            "role": "user",
            "content": prompt,
        }],
    )

    print("\n\nEMAIL PROMPT", prompt)

    return raw_response.choices[0].message.content

def load_model(filename):
    with open(filename, 'rb') as file:
        return pickle.load(file)


xgboost_model = load_model('xgb_model.pkl')

naive_bayes_model = load_model('nb_model.pkl')

decision_tree_model = load_model('dt_model.pkl')

svm_model = load_model('svm_model.pkl')

knn_model = load_model('knn_model.pkl')

xgboost_SMOTE_model = load_model('xgboost-SMOTE.pkl')


def prepare_input(credit_score, location, gender, age, tenure, balance,
                  num_products, has_credit_card, is_active_member,
                  estimated_salary):
    input_dict = {
        "CreditScore": credit_score,
        "Age": age,
        "Tenure": tenure,
        "Balance": balance,
        "NumOfProducts": num_products,
        "HasCrCard": int(has_credit_card),
        "IsActiveMember": int(is_active_member),
        "EstimatedSalary": estimated_salary,
        'Geography_France': 1 if location == 'France' else 0,
        "Geograpghy_Germany": 1 if location == 'Germany' else 0,
        "Geography_Spain": 1 if location == 'Spain' else 0,
        "Gender_Male": 1 if gender == 'Male' else 0,
        "Gender_Female": 1 if gender == 'Female' else 0
    }

    input_df = pd.DataFrame([input_dict])
    return input_df, input_dict


def make_predictions(input_df, input_dict):
    probabilities = {
        'XGBoost': xgboost_model.predict_proba(input_df)[0][1],
        'K-Nearest Neighbors': knn_model.predict_proba(input_df)[0][1],
    }

    avg_probability = np.mean(list(probabilities.values()))

    st.markdown('### Model Probabilities')
    for model, prob in probabilities.items():
        st.write(f'{model} {prob}')
    st.write(f"Average Probability: {avg_probability}")
    return avg_probability


st.title("Customer Churn Prediction")

df = pd.read_csv('churn.csv')

customers = [
    f"{row['CustomerId']} - {row['Surname']}" for _, row in df.iterrows()
]

selected_customer_option = st.selectbox("Select a customer", customers)

if selected_customer_option:
    selected_customer_id = int(selected_customer_option.split(" - ")[0])

    print("Selected Customer ID", selected_customer_id)

    selected_surname = selected_customer_option.split(" - ")[1]

    print("Surname", selected_surname)

    selected_customer = df.loc[df['CustomerId'] ==
                               selected_customer_id].iloc[0]

    print("Selected Customer", selected_customer)

    col1, col2 = st.columns(2)

    with col1:
        credit_score = st.number_input("Credit Score",
                                       min_value=300,
                                       max_value=850,
                                       value=int(
                                           selected_customer['CreditScore']))

        location = st.selectbox("Location", ["Spain", "France", "Germany"],
                                index=["Spain", "France", "Germany"
                                       ].index(selected_customer["Geography"]))
        gender = st.radio(
            "Gender", ['Male', "Female"],
            index=0 if selected_customer["Gender"] == "Male" else 1)

        age = st.number_input("Age",
                              min_value=10,
                              max_value=100,
                              value=int(selected_customer['Age']))

        tenure = st.number_input("Tenure (years)",
                                 min_value=2,
                                 max_value=50,
                                 value=int(selected_customer['Tenure']))

    with col2:
        balance = st.number_input("Balance",
                                  min_value=0.0,
                                  value=float(selected_customer['Balance']))

        num_products = st.number_input("Number of Products",
                                       min_value=1,
                                       max_value=10,
                                       value=int(
                                           selected_customer['NumOfProducts']))

        has_credit_card = st.checkbox("Has Credit Card",
                                      value=selected_customer['HasCrCard'])

        is_active_member = st.checkbox(
            "Is Active Member",
            value=bool(selected_customer['IsActiveMember']))

        estimated_salary = st.number_input(
            "Estimated Salary",
            min_value=0.0,
            value=float(selected_customer['EstimatedSalary']))

    input_df, input_dict = prepare_input(credit_score, location, gender, age,
                                         tenure, balance, num_products,
                                         has_credit_card, is_active_member,
                                         estimated_salary)

    avg_probability = make_predictions(input_df, input_dict)

    explanation = explain_prediction(avg_probability, input_dict, selected_customer["Surname"])

    st.markdown("---")

    st.subheader("Explanation of Prediction")

    st.markdown(explanation)

    email = generate_email(avg_probability, input_dict, explanation, selected_customer['Surname'])

    st.markdown('---')

    st.subheader("Personalized Email")

    st.markdown(email)

    # st.subheader("Explanation of Prediction")

    # st.markdown(explanation)
