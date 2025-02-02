import pandas as pd
import numpy as np
from sklearn.svm import SVC
import joblib
import shap
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import classification_report, confusion_matrix
import matplotlib.pyplot as plt
from sklearn.metrics import roc_curve, auc
from sklearn.feature_extraction.text import TfidfVectorizer
import gender_guesser.detector as gender

def read_datasets():
    genuine_users = pd.read_csv("data/gusers.csv")
    fake_users = pd.read_csv("data/fusers.csv")
    x = pd.concat([genuine_users, fake_users], ignore_index=True)
    y = [0] * len(fake_users) + [1] * len(genuine_users)
    return x, y

def predict_sex(names):
    detector = gender.Detector()
    first_names = names.str.split(' ').str.get(0)
    sex = first_names.apply(lambda x: detector.get_gender(x).split()[0])
    sex_dict = {'female': -2, 'mostly_female': -1, 'unknown': 0, 'mostly_male': 1, 'male': 2}
    return sex.map(sex_dict).fillna(0).astype(int)

def extract_features(df):
    # Convert numeric columns
    df['followers_count'] = pd.to_numeric(df['followers_count'], errors='coerce')
    df['following_count'] = pd.to_numeric(df['following_count'], errors='coerce')
    df['subscription_count'] = pd.to_numeric(df['subscription_count'], errors='coerce')
    
    # Fill NaN values with 0
    df.fillna(0, inplace=True)
    
    # Predict gender from username
    if 'username' in df.columns:
        df['sex_code'] = predict_sex(df['username'])
        df.to_csv("data/updated_users.csv", index=False)
    else:
        df['sex_code'] = 0

    # Extract creation month and year from 'created_at'
    if 'created_at' in df.columns:
        df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce', dayfirst=True)
        df['created_month'] = df['created_at'].dt.month.fillna(0).astype(int)
        df['created_year'] = df['created_at'].dt.year.fillna(0).astype(int)
    else:
        df['created_month'] = df['created_year'] = 0

    # Feature extraction from 'description'
    if 'description' in df.columns:
        df['description'] = df['description'].fillna("").astype(str)
        df['description_length'] = df['description'].apply(len)
        
        vectorizer = TfidfVectorizer(max_features=50)  # Reduce max_features for faster processing
        tfidf_matrix = vectorizer.fit_transform(df['description'])
        tfidf_df = pd.DataFrame(tfidf_matrix.toarray(), columns=vectorizer.get_feature_names_out())
        df = pd.concat([df, tfidf_df], axis=1)
        
    else:
        df['description_length'] = 0

    feature_columns_to_use = [
        'followers_count', 'following_count', 'subscription_count',
        'sex_code', 'created_month', 'created_year', 'is_verified', 'description_length'
    ]
    
    if 'description' in df.columns:
        feature_columns_to_use += vectorizer.get_feature_names_out().tolist()

    return df[feature_columns_to_use]

def train_svm(X, y):
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.20, random_state=42, stratify=y)

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    svm_model = SVC(probability=True, random_state=42)

    # Optimize hyperparameter search
    param_grid = {
        'C': [0.1, 1, 10],
        'kernel': ['linear'],  # Start with a linear kernel for speed
        'gamma': ['scale']
    }

    grid_search = GridSearchCV(svm_model, param_grid, cv=3, scoring='accuracy', verbose=1, n_jobs=-1)
    grid_search.fit(X_train_scaled, y_train)

    print("Best parameters found: ", grid_search.best_params_)
    clf = grid_search.best_estimator_

    predictions = clf.predict(X_test_scaled)
    predicted_probabilities = clf.predict_proba(X_test_scaled)[:, 1]

    print("Classification Report (SVM):\n", classification_report(y_test, predictions))
    print("Confusion Matrix (SVM):\n", confusion_matrix(y_test, predictions))

    return y_test, predictions, predicted_probabilities, clf, X_train_scaled, X_test_scaled, scaler

def save_model_and_scaler(model, scaler):
    joblib.dump(model, 'svm_model.pkl')
    joblib.dump(scaler, 'scaler.pkl')

def plot_confusion_matrix(cm):
    plt.figure()
    plt.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
    plt.title('Confusion Matrix (SVM)')
    plt.colorbar()
    target_names = ['Fake', 'Genuine']
    tick_marks = np.arange(len(target_names))
    plt.xticks(tick_marks, target_names, rotation=45)
    plt.yticks(tick_marks, target_names)
    fmt = '.2f'
    thresh = cm.max() / 2.
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            value = cm[i, j]
            plt.text(j, i, f'{value:{fmt}}',
                     horizontalalignment="center",
                     color="white" if value > thresh else "black")
    plt.tight_layout()
    plt.ylabel('True label')
    plt.xlabel('Predicted label')
    plt.show()

def plot_roc_curve(y_true, y_scores):
    fpr, tpr, _ = roc_curve(y_true, y_scores)
    roc_auc = auc(fpr, tpr)
    plt.figure()
    plt.plot(fpr, tpr, label='ROC curve (area = {:.2f})'.format(roc_auc))
    plt.plot([0, 1], [0, 1], 'k--')
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('Receiver Operating Characteristic')
    plt.legend(loc="lower right")
    plt.show()

def explain_with_shap(model, X_train_scaled, X_test_scaled):
    explainer = shap.KernelExplainer(model.predict, X_train_scaled)
    shap_values = explainer.shap_values(X_test_scaled)

    shap.summary_plot(shap_values, X_test_scaled)

def main():
    print("Reading datasets...")
    x, y = read_datasets()
    print("Extracting features...")
    x = extract_features(x)
    y = np.array(y)
    y_test, predictions, predicted_probabilities, model, X_train_scaled, X_test_scaled, scaler = train_svm(x, y)

    cm = confusion_matrix(y_test, predictions)
    plot_confusion_matrix(cm)
    plot_roc_curve(y_test, predicted_probabilities)

    save_model_and_scaler(model, scaler)

    explain_with_shap(model, X_train_scaled, X_test_scaled)

if __name__ == "__main__":
    main()
