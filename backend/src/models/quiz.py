# Models for Quizzes, Questions, Answers, and User Attempts

from sqlalchemy.dialects.mysql import INTEGER
from . import db # Assuming db is initialized in __init__.py of the models directory or src
import datetime

class Quiz(db.Model):
    __tablename__ = "quizzes"
    id = db.Column(INTEGER(unsigned=True), primary_key=True, autoincrement=True)
    # Link to the main content item, if the quiz is a type of content
    content_item_id = db.Column(INTEGER(unsigned=True), db.ForeignKey("content_items.id"), nullable=True, unique=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_by_id = db.Column(INTEGER(unsigned=True), db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    content_item = db.relationship("ContentItem", backref=db.backref("quiz_details", uselist=False, cascade="all, delete-orphan"))
    creator = db.relationship("User", backref=db.backref("created_quizzes", lazy="dynamic"))
    questions = db.relationship("Question", back_populates="quiz", lazy="dynamic", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Quiz {self.title}>"

class Question(db.Model):
    __tablename__ = "questions"
    id = db.Column(INTEGER(unsigned=True), primary_key=True, autoincrement=True)
    quiz_id = db.Column(INTEGER(unsigned=True), db.ForeignKey("quizzes.id"), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    # Example: 'multiple_choice', 'true_false', 'short_answer'. Consider an Enum or a QuestionType table.
    question_type = db.Column(db.String(50), nullable=False, default="multiple_choice") 
    order = db.Column(db.Integer, nullable=False, default=0) # To maintain question order
    # For multiple choice, store correct answer_option_id or a list if multiple correct answers
    # For true/false, could store True/False directly or link to an AnswerOption
    # For short_answer, might need manual grading or regex matching (more complex)
    # For simplicity, let's assume single correct answer for MCQs for now.

    quiz = db.relationship("Quiz", back_populates="questions")
    answer_options = db.relationship("AnswerOption", back_populates="question", lazy="dynamic", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Question {self.id} - Quiz {self.quiz_id}>"

class AnswerOption(db.Model):
    __tablename__ = "answer_options"
    id = db.Column(INTEGER(unsigned=True), primary_key=True, autoincrement=True)
    question_id = db.Column(INTEGER(unsigned=True), db.ForeignKey("questions.id"), nullable=False)
    option_text = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, default=False, nullable=False)

    question = db.relationship("Question", back_populates="answer_options")

    def __repr__(self):
        return f"<AnswerOption {self.id} for Question {self.question_id}>"

class UserQuizAttempt(db.Model):
    __tablename__ = "user_quiz_attempts"
    id = db.Column(INTEGER(unsigned=True), primary_key=True, autoincrement=True)
    user_id = db.Column(INTEGER(unsigned=True), db.ForeignKey("users.id"), nullable=False)
    quiz_id = db.Column(INTEGER(unsigned=True), db.ForeignKey("quizzes.id"), nullable=False)
    started_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    score = db.Column(db.Float, nullable=True) # Can be percentage or raw score

    user = db.relationship("User", backref=db.backref("quiz_attempts", lazy="dynamic"))
    quiz = db.relationship("Quiz", backref=db.backref("attempts", lazy="dynamic"))
    answers = db.relationship("UserAnswer", back_populates="attempt", lazy="dynamic", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<UserQuizAttempt User {self.user_id} - Quiz {self.quiz_id}>"

class UserAnswer(db.Model):
    __tablename__ = "user_answers"
    id = db.Column(INTEGER(unsigned=True), primary_key=True, autoincrement=True)
    user_quiz_attempt_id = db.Column(INTEGER(unsigned=True), db.ForeignKey("user_quiz_attempts.id"), nullable=False)
    question_id = db.Column(INTEGER(unsigned=True), db.ForeignKey("questions.id"), nullable=False)
    selected_answer_option_id = db.Column(INTEGER(unsigned=True), db.ForeignKey("answer_options.id"), nullable=True)
    # For short_answer type, this could store the text input
    # answer_text = db.Column(db.Text, nullable=True) 
    is_correct = db.Column(db.Boolean, nullable=True) # Determined after submission
    submitted_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    attempt = db.relationship("UserQuizAttempt", back_populates="answers")
    question = db.relationship("Question")
    selected_answer_option = db.relationship("AnswerOption")

    def __repr__(self):
        return f"<UserAnswer Attempt {self.user_quiz_attempt_id} - Question {self.question_id}>"

