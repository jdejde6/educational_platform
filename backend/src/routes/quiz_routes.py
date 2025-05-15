# Routes for Quizzes, Questions, and User Attempts

from flask import Blueprint, request, jsonify
from ..models import db
from ..models.quiz import Quiz, Question, AnswerOption, UserQuizAttempt, UserAnswer
from ..models.content import ContentItem # For linking quiz to a content item
from ..models.user import User # For created_by_id and user_id in attempts
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError
import datetime

quiz_bp = Blueprint("quiz_bp", __name__, url_prefix="/api/quizzes")

# Helper function to get current user (placeholder - same as in content_routes.py)
def get_current_user_id():
    user = User.query.first()
    if user:
        return user.id
    # This fallback for dummy user creation should ideally not be hit if users are managed properly.
    print("WARN: No users found, creating a dummy user with id 1 for testing quiz creation.")
    dummy_user = User(username="dummy_quiz_creator", email="dummy_quiz@example.com", password_hash="dummy")
    db.session.add(dummy_user)
    try:
        db.session.commit()
        return dummy_user.id
    except Exception as e:
        db.session.rollback()
        print(f"Error creating dummy user for quiz: {e}")
        return None

# --- Quiz Routes ---
@quiz_bp.route("", methods=["POST"])
def create_quiz():
    data = request.get_json()
    if not data or not data.get("title"):
        return jsonify({"error": "Missing title for quiz"}), 400

    creator_id = get_current_user_id()
    if not creator_id:
        return jsonify({"error": "Could not determine creator. User authentication needed."}), 500

    new_quiz = Quiz(
        title=data["title"],
        description=data.get("description"),
        created_by_id=creator_id,
        content_item_id=data.get("content_item_id") # Optional: link to a ContentItem
    )

    # Add questions and answer options if provided in the same request
    questions_data = data.get("questions", [])
    for q_data in questions_data:
        if not q_data.get("question_text") or not q_data.get("question_type"):
            # Not returning error here, but logging it. Quiz can be created without questions initially.
            print(f"Skipping question due to missing text or type: {q_data}")
            continue
        
        question = Question(
            question_text=q_data["question_text"],
            question_type=q_data["question_type"],
            order=q_data.get("order", 0)
        )
        options_data = q_data.get("answer_options", [])
        for opt_data in options_data:
            if not opt_data.get("option_text"):
                print(f"Skipping answer option due to missing text: {opt_data}")
                continue
            answer_option = AnswerOption(
                option_text=opt_data["option_text"],
                is_correct=opt_data.get("is_correct", False)
            )
            question.answer_options.append(answer_option)
        new_quiz.questions.append(question)

    try:
        db.session.add(new_quiz)
        db.session.commit()
        return jsonify({"message": "Quiz created successfully", "id": new_quiz.id}), 201
    except IntegrityError as e:
        db.session.rollback()
        return jsonify({"error": "Database integrity error", "details": str(e)}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Could not create quiz", "details": str(e)}), 500

@quiz_bp.route("", methods=["GET"])
def get_all_quizzes():
    quizzes = Quiz.query.options(joinedload(Quiz.questions).joinedload(Question.answer_options)).all()
    output = []
    for quiz in quizzes:
        quiz_data = {
            "id": quiz.id,
            "title": quiz.title,
            "description": quiz.description,
            "created_by_id": quiz.created_by_id,
            "content_item_id": quiz.content_item_id,
            "created_at": quiz.created_at.isoformat(),
            "num_questions": quiz.questions.count()
        }
        output.append(quiz_data)
    return jsonify(output), 200

@quiz_bp.route("/<int:quiz_id>", methods=["GET"])
def get_quiz_details(quiz_id):
    quiz = Quiz.query.options(
        joinedload(Quiz.questions).joinedload(Question.answer_options)
    ).get(quiz_id)

    if not quiz:
        return jsonify({"error": "Quiz not found"}), 404

    quiz_data = {
        "id": quiz.id,
        "title": quiz.title,
        "description": quiz.description,
        "created_by_id": quiz.created_by_id,
        "content_item_id": quiz.content_item_id,
        "created_at": quiz.created_at.isoformat(),
        "questions": [
            {
                "id": q.id,
                "question_text": q.question_text,
                "question_type": q.question_type,
                "order": q.order,
                "answer_options": [
                    {
                        "id": opt.id,
                        "option_text": opt.option_text,
                        # IMPORTANT: Do not expose is_correct in a general GET request for the quiz structure.
                        # This should only be available when checking answers or for admins.
                        # For now, we omit it for students taking the quiz.
                    } for opt in q.answer_options
                ]
            } for q in quiz.questions
        ]
    }
    return jsonify(quiz_data), 200

@quiz_bp.route("/<int:quiz_id>", methods=["PUT"])
def update_quiz(quiz_id):
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return jsonify({"error": "Quiz not found"}), 404

    data = request.get_json()
    quiz.title = data.get("title", quiz.title)
    quiz.description = data.get("description", quiz.description)
    quiz.content_item_id = data.get("content_item_id", quiz.content_item_id)
    quiz.updated_at = datetime.datetime.utcnow()
    # Note: Updating questions/answers within a quiz via this PUT is complex.
    # Typically, you would have separate endpoints for managing questions within a quiz.
    # For simplicity, this example only updates quiz-level details.
    try:
        db.session.commit()
        return jsonify({"message": "Quiz updated successfully", "id": quiz.id}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Could not update quiz", "details": str(e)}), 500

@quiz_bp.route("/<int:quiz_id>", methods=["DELETE"])
def delete_quiz(quiz_id):
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return jsonify({"error": "Quiz not found"}), 404
    try:
        db.session.delete(quiz)
        db.session.commit()
        return jsonify({"message": "Quiz deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Could not delete quiz", "details": str(e)}), 500

# --- Question Management (within a Quiz) ---
# These would typically be nested routes like /api/quizzes/<quiz_id>/questions
# For simplicity, keeping them separate for now but linked via quiz_id in payload/path

@quiz_bp.route("/<int:quiz_id>/questions", methods=["POST"])
def add_question_to_quiz(quiz_id):
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return jsonify({"error": "Quiz not found"}), 404

    data = request.get_json()
    if not data or not data.get("question_text") or not data.get("question_type"):
        return jsonify({"error": "Missing question_text or question_type"}), 400

    new_question = Question(
        quiz_id=quiz_id,
        question_text=data["question_text"],
        question_type=data["question_type"],
        order=data.get("order", 0)
    )

    options_data = data.get("answer_options", [])
    for opt_data in options_data:
        if not opt_data.get("option_text"):
            continue # Skip if no text
        answer_option = AnswerOption(
            option_text=opt_data["option_text"],
            is_correct=opt_data.get("is_correct", False)
        )
        new_question.answer_options.append(answer_option)
    
    try:
        db.session.add(new_question)
        db.session.commit()
        return jsonify({"message": "Question added to quiz", "id": new_question.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Could not add question", "details": str(e)}), 500

# --- User Quiz Attempt Routes ---

@quiz_bp.route("/<int:quiz_id>/attempt", methods=["POST"])
def start_quiz_attempt(quiz_id):
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "User not authenticated"}), 401

    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return jsonify({"error": "Quiz not found"}), 404

    # Check for existing incomplete attempts if needed (policy decision)

    new_attempt = UserQuizAttempt(user_id=user_id, quiz_id=quiz_id)
    try:
        db.session.add(new_attempt)
        db.session.commit()
        # Return the quiz structure along with attempt ID
        quiz_details = get_quiz_details(quiz_id).get_json()
        return jsonify({
            "message": "Quiz attempt started", 
            "attempt_id": new_attempt.id,
            "quiz_details": quiz_details
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Could not start quiz attempt", "details": str(e)}), 500

@quiz_bp.route("/attempts/<int:attempt_id>/submit", methods=["POST"])
def submit_quiz_answers(attempt_id):
    user_id = get_current_user_id()
    if not user_id:
        return jsonify({"error": "User not authenticated"}), 401

    attempt = UserQuizAttempt.query.filter_by(id=attempt_id, user_id=user_id).first()
    if not attempt:
        return jsonify({"error": "Quiz attempt not found or does not belong to user"}), 404
    
    if attempt.completed_at:
        return jsonify({"error": "Quiz attempt already completed"}), 400

    answers_data = request.get_json().get("answers", []) # Expects a list of {"question_id": X, "selected_answer_option_id": Y}
    
    total_questions = 0
    correct_answers = 0

    for ans_data in answers_data:
        question_id = ans_data.get("question_id")
        selected_option_id = ans_data.get("selected_answer_option_id")

        question = Question.query.get(question_id)
        if not question or question.quiz_id != attempt.quiz_id:
            print(f"Warning: Question {question_id} not found in quiz for attempt {attempt_id}")
            continue
        
        total_questions +=1
        is_correct_submission = False
        if selected_option_id:
            selected_option = AnswerOption.query.filter_by(id=selected_option_id, question_id=question_id).first()
            if selected_option and selected_option.is_correct:
                correct_answers += 1
                is_correct_submission = True
        
        user_answer = UserAnswer(
            user_quiz_attempt_id=attempt_id,
            question_id=question_id,
            selected_answer_option_id=selected_option_id,
            is_correct=is_correct_submission
        )
        db.session.add(user_answer)

    attempt.completed_at = datetime.datetime.utcnow()
    # Calculate score (simple percentage for now)
    # Ensure total_questions is not zero to avoid division by zero error
    attempt.score = (correct_answers / total_questions * 100) if total_questions > 0 else 0

    try:
        db.session.commit()
        return jsonify({
            "message": "Quiz submitted successfully", 
            "attempt_id": attempt.id, 
            "score": attempt.score,
            "correct_answers": correct_answers,
            "total_questions": total_questions
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Could not submit quiz answers", "details": str(e)}), 500

@quiz_bp.route("/attempts/<int:attempt_id>/results", methods=["GET"])
def get_quiz_attempt_results(attempt_id):
    user_id = get_current_user_id() # Or admin check
    attempt = UserQuizAttempt.query.options(
        joinedload(UserQuizAttempt.answers).joinedload(UserAnswer.question).joinedload(Question.answer_options),
        joinedload(UserQuizAttempt.answers).joinedload(UserAnswer.selected_answer_option)
    ).filter_by(id=attempt_id).first()
    # Add user_id check if results are private to the user who took it
    # if not attempt or attempt.user_id != user_id:
    #     return jsonify({"error": "Attempt not found or access denied"}), 404
    if not attempt:
         return jsonify({"error": "Attempt not found"}), 404

    if not attempt.completed_at:
        return jsonify({"error": "Quiz attempt not yet completed"}), 400

    results_data = {
        "attempt_id": attempt.id,
        "quiz_id": attempt.quiz_id,
        "user_id": attempt.user_id,
        "started_at": attempt.started_at.isoformat(),
        "completed_at": attempt.completed_at.isoformat(),
        "score": attempt.score,
        "answers": [
            {
                "question_id": ans.question_id,
                "question_text": ans.question.question_text,
                "selected_answer_option_id": ans.selected_answer_option_id,
                "selected_answer_text": ans.selected_answer_option.option_text if ans.selected_answer_option else None,
                "is_correct": ans.is_correct,
                "correct_options": [opt.id for opt in ans.question.answer_options if opt.is_correct]
            } for ans in attempt.answers
        ]
    }
    return jsonify(results_data), 200

