# QuizPro - AI-Powered Question Generation Platform

## 📝 Description
QuizPro is an intelligent educational platform developed as part of my Master's final project. It leverages AI to automatically generate questions from textual content, enhancing the learning experience. It offers two main features:

## **Question Generator: Transforms any text into relevant questions.**

## **Exam Generator: Creates complete exams with different types of questions.**

---

## 🚀 Features

### **Project 1: Question Generator**
- Converts text into questions.
- Customizable number of questions (1 to 10).
- Real-time text processing.
- Character limit protection (maximum 5000 characters).
- Responsive design.
- Loading indicators to enhance user experience.

### **Project 2: Exam Generator**
- Generates different types of questions:
  - Multiple Choice Questions (MCQs)
  - True/False
  - Open-ended questions
  - Fill-in-the-Blanks
- Difficulty level selection.
- PDF export functionality.
- Customizable number of questions.

---

## 🤖 AI Integration

### **Groq API with Mixtral-8x7b Model** (for Project 2)
The integration of the Groq API enables the generation of exams with questions tailored to educational needs. Here is an overview of the implementation:

1. **API Configuration**: Connects to the AI model via API requests.
2. **Question Generation**: Uses the Mixtral-8x7b model to ensure question relevance and diversity.

---

## 🛠️ Technologies Used
- **Backend**: Python, Flask.
- **Frontend**: HTML5, CSS3, JavaScript.
- **AI Model**: BART (fine-tuned for question generation).
- **Database**: MongoDB.
- **Authentication**: Session-based authentication.

---

## 📋 Prerequisites
- **Python** 3.11 or later.
- **MongoDB** installed and configured.
- Install Python dependencies via `requirements.txt`.

---

## ⚙️ Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your_username/quizpro.git
   cd quizpro
   ```
