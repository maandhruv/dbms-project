from flask import Flask, jsonify, request, render_template
from flask_sqlalchemy import SQLAlchemy
import pymysql
pymysql.install_as_MySQLdb()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:password@localhost/student_management'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Models
class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    email = db.Column(db.String(50), unique=True, nullable=False)
    
    # Relationship with Enrollment
    courses = db.relationship('Enrollment', back_populates='student', overlaps="students,enrollments")

class Course(db.Model):
    __tablename__ = 'courses'
    id = db.Column(db.Integer, primary_key=True)
    course_name = db.Column(db.String(50), nullable=False)
    course_code = db.Column(db.String(10), unique=True, nullable=False)
    
    # Relationship with Enrollment
    students = db.relationship('Enrollment', back_populates='course', overlaps="students,enrollments")

class Enrollment(db.Model):
    __tablename__ = 'enrollments'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    
    # Define relationships back to Student and Course
    student = db.relationship('Student', back_populates='courses')
    course = db.relationship('Course', back_populates='students')

# Routes
@app.route('/')
def home():
    total_students = Student.query.count()
    total_courses = Course.query.count()
    total_enrollments = Enrollment.query.count()
    return render_template('index.html', 
                           total_students=total_students, 
                           total_courses=total_courses, 
                           total_enrollments=total_enrollments)

@app.route('/students')
def students_page():
    return render_template('students.html')

@app.route('/courses')
def courses_page():
    return render_template('courses.html')

@app.route('/enrollments')
def enrollments_page():
    students = Student.query.all()
    courses = Course.query.all()
    return render_template('enrollments.html', students=students, courses=courses)

@app.route('/search')
def search_page():
    return render_template('search.html')

# Student CRUD API
@app.route('/api/students', methods=['GET', 'POST'])
def manage_students():
    if request.method == 'POST':
        data = request.json
        new_student = Student(name=data['name'], age=data['age'], email=data['email'])
        db.session.add(new_student)
        db.session.commit()
        return jsonify({'message': 'Student added successfully'}), 201
    else:
        students = Student.query.all()
        return jsonify([{'id': s.id, 'name': s.name, 'age': s.age, 'email': s.email} for s in students])

@app.route('/api/students/<int:id>', methods=['PUT', 'DELETE'])
def modify_student(id):
    student = Student.query.get_or_404(id)
    
    if request.method == 'PUT':
        data = request.json
        print("Received data for update:", data)  # Debugging line

        if 'name' in data:
            student.name = data['name']
        if 'age' in data:
            student.age = data['age']
        if 'email' in data:
            student.email = data['email']
        
        db.session.commit()
        return jsonify({'message': 'Student updated successfully'})
    
    elif request.method == 'DELETE':
        db.session.delete(student)
        db.session.commit()
        return jsonify({'message': 'Student deleted successfully'})


# Course CRUD API
@app.route('/api/courses', methods=['GET', 'POST'])
def manage_courses():
    if request.method == 'POST':
        data = request.json
        new_course = Course(course_name=data['course_name'], course_code=data['course_code'])
        db.session.add(new_course)
        db.session.commit()
        return jsonify({'message': 'Course added successfully'}), 201
    else:
        courses = Course.query.all()
        return jsonify([{'id': c.id, 'course_name': c.course_name, 'course_code': c.course_code} for c in courses])

@app.route('/api/courses/<int:id>', methods=['PUT', 'DELETE'])
def modify_course(id):
    course = Course.query.get_or_404(id)
    if request.method == 'PUT':
        data = request.json
        course.course_name = data['course_name']
        course.course_code = data['course_code']
        db.session.commit()
        return jsonify({'message': 'Course updated successfully'})
    elif request.method == 'DELETE':
        db.session.delete(course)
        db.session.commit()
        return jsonify({'message': 'Course deleted successfully'})

@app.route('/api/enrollments/<int:id>', methods=['DELETE'])
def delete_enrollment(id):
    enrollment = Enrollment.query.get_or_404(id)
    db.session.delete(enrollment)
    db.session.commit()
    return jsonify({'message': 'Enrollment deleted successfully'})

@app.route('/api/enrollments', methods=['GET', 'POST'])
def manage_enrollments():
    if request.method == 'POST':
        data = request.get_json()
        student_id = data['student_id']
        course_id = data['course_id']

        # Check if the enrollment already exists
        existing_enrollment = Enrollment.query.filter_by(student_id=student_id, course_id=course_id).first()
        if existing_enrollment:
            return jsonify({"error": "Enrollment already exists"}), 409

        new_enrollment = Enrollment(student_id=student_id, course_id=course_id)
        db.session.add(new_enrollment)
        db.session.commit()
        return jsonify({"message": "Enrollment created successfully"}), 201
    else:
        # Fetch enrollments along with student name and course code
        enrollments = db.session.query(
            Enrollment.id,
            Student.name.label("student_name"),
            Course.course_code.label("course_code")
        ).join(Student, Enrollment.student_id == Student.id)\
         .join(Course, Enrollment.course_id == Course.id).all()

        return jsonify([
            {'id': e.id, 'student_name': e.student_name, 'course_code': e.course_code}
            for e in enrollments
        ])


from sqlalchemy import text

@app.route('/search_student')
def search_student():
    student_name = request.args.get('student_name')
    
    # Raw SQL query to search for the student by name
    result = db.session.execute(
        text("SELECT * FROM students WHERE name = :name"), {"name": student_name}
    )
    student_row = result.fetchone()
    if student_row:
        # Fetch the student's courses using a raw SQL query
        courses_result = db.session.execute(
            text("""
                SELECT c.* FROM courses c
                JOIN enrollments e ON c.id = e.course_id
                WHERE e.student_id = :student_id
            """), {"student_id": student_row.id}
        )
        courses = courses_result.fetchall()
        return render_template('search.html', student=student_row, courses=courses)
    else:
        message = f"Student '{student_name}' not found."
        return render_template('search.html', message=message)

@app.route('/search_course')
def search_course():
    course_name = request.args.get('course_name')
    
    # Raw SQL query to search for the course by name
    result = db.session.execute(
        text("SELECT * FROM courses WHERE course_name = :course_name"), {"course_name": course_name}
    )
    course_row = result.fetchone()

    if course_row:
        # Fetch students enrolled in the course using a raw SQL query
        students_result = db.session.execute(
            text("""
                SELECT s.* FROM students s
                JOIN enrollments e ON s.id = e.student_id
                WHERE e.course_id = :course_id
            """), {"course_id": course_row.id}
        )
        students = students_result.fetchall()
        return render_template('search.html', course=course_row, students=students)
    else:
        message = f"Course '{course_name}' not found."
        return render_template('search.html', message=message)


# Initialize database tables
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)
