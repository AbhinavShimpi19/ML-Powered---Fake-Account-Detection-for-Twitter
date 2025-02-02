# **ML-Powered Fake Account Detection for Twitter**

## **Overview**
This project aims to detect fake accounts on Twitter using **Machine Learning (ML)** techniques. The model analyzes various features of user profiles and their activity patterns to distinguish between real and fake accounts.

## **Features**
- **Automated Fake Account Detection**: Uses ML algorithms to classify accounts.
- **Real-time Analysis**: Processes Twitter data in real time.
- **Scalability**: Can be extended to detect fake accounts on other social media platforms.
- **Custom Model Training**: Users can train models with their datasets.

## **Tech Stack**
- **Programming Language**: Python
- **Libraries & Frameworks**:
  - `scikit-learn` (ML models)
  - `pandas` (Data processing)
  - `numpy` (Numerical computations)
  - `tweepy` (Twitter API integration)
  - `flask` (Web API for detection system)

## **Installation & Setup**
### **1. Clone the Repository**
```bash
 git clone https://github.com/AbhinavShimpi19/ML-Powered--Fake-Account-Detection-for-Twitter.git
 cd Fake-Account-Detection
```
### **2. Create a Virtual Environment**
```bash
 python -m venv venv
 source venv/bin/activate  # On macOS/Linux
 venv\Scripts\activate     # On Windows
```
### **3. Install Dependencies**
```bash
 pip install -r requirements.txt
```

## **Usage**
### **1. Train the Model**
```bash
 python train.py --dataset data/fake_accounts.csv
```
### **2. Run the Fake Account Detection System**
```bash
 python app.py
```
### **3. Test with a Sample Twitter Account**
Use the API endpoint to check if an account is fake:
```bash
 curl -X POST http://127.0.0.1:5000/predict -d '{"username": "some_twitter_user"}' -H "Content-Type: application/json"
```

## **Contributing**
We welcome contributions! Follow these steps to contribute:
1. Fork the repository.
2. Create a new branch: `git checkout -b feature-branch`
3. Commit your changes: `git commit -m 'Add new feature'`
4. Push to the branch: `git push origin feature-branch`
5. Open a pull request.

## **License**
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## **Author**
**Abhinav Shimpi**
- [GitHub](https://github.com/AbhinavShimpi19)
- [LinkedIn](https://www.linkedin.com/in/abhinav-shimpi/)

