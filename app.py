from flask import Flask,request,jsonify,make_response
from flask_sqlalchemy import SQLAlchemy
import uuid
from werkzeug.security import generate_password_hash,check_password_hash
import jwt
import datetime
from functools import wraps

app=Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI']='postgresql://postgres:morgan8514@127.0.0.1:5432/api_test'
app.config['SECRET_KEY']='secretkey'

db=SQLAlchemy(app)




# creating tables
class User(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    public_id=db.Column(db.String(200),unique=False,nullable=True)
    name = db.Column(db.String(50))
    password= db.Column(db.String(200))
    admin= db.Column(db.Boolean)

    def create():
        db.create_all()

class Todo(db.Model):
    id= db.Column(db.Integer,primary_key=True)
    text= db.Column(db.String(200))
    complete=db.Column(db.Boolean)
    user_id= db.Column(db.Integer)

User.create()

# creating the decoratore so that every route should take in require token
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token= None

        # checking if the ytoken already exists in the header
        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']
        if not token:
            return jsonify({"message":"token is missing"})

        try:
            # DECODIN THE TOKEN
            data=jwt.decode(token,app.config['SECRET_KEY'])
            # retrieving the public_id encoded in the token and matching it to the specific user
            user_for_public_id = User.query.filter_by(public_id=data['public_id']).first()

        except:
            return jsonify({"message":" token is invalid"}),401
  
        return f(user_for_public_id,*args, **kwargs)
    return decorated


        

# creating user route
@app.route('/user',methods=['POST'])
@token_required
def create_user(user_for_public_id):


    data= request.get_json()
    

    hashed_password = generate_password_hash(data['password'],method='sha256')

    new_user= User(public_id=str(uuid.uuid4()), name=data['name'], password=hashed_password, admin=False)

    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message' : 'new user created'})

# fetching all user route
@app.route('/user',methods=['GET'])
@token_required
def get_all_users(user_for_public_id):

        # making sure that only admins na query data from yhe database
    if  user_for_public_id.admin==False:
        return jsonify({"message":"cannot perfon above function! u are not admin"})


    # querying for all users
    users=User.query.all()
    output=[]

    for user in users:
        user_data={}
        user_data['public_id']=user.public_id
        user_data['name']= user.name
        user_data['password']= user.password
        user_data['admin']=user.admin
        output.append(user_data)


    return jsonify({"user":output})

@app.route('/user/<public_id>',methods=['GET'])
@token_required
def get_one_user(user_for_public_id,public_id):

        # making sure that only admins na query data from yhe database
    if not user_for_public_id.admin:
        return jsonify({"message":"cannot perfon above function! u are not admin"})


    single_user=User.query.filter_by(public_id=public_id).first()
    if not single_user:
        return jsonify({"message":"no user found!"})

    user_data={}
    user_data['public_id']= single_user.public_id
    user_data['name']= single_user.name
    user_data['password']=single_user.password
    user_data['admin']=single_user.admin

    return jsonify({"message": user_data})

@app.route('/user/<public_id>',methods=['PUT'])
@token_required
def promote_user(user_for_public_id,public_id):

        # making sure that only admins na query data from yhe database
    if not user_for_public_id.admin:
        return jsonify({"message":"cannot perfon above function! u are not admin"})


    single_user=User.query.filter_by(public_id=public_id).first()
    if not single_user:
        return jsonify({"message":" no user found! "})
    single_user.admin=True
    db.session.commit()

    return jsonify({"message" : "User has been promoted!"})

@app.route('/user/<public_id>',methods=['DELETE'])
@token_required
def delete_user(user_for_public_id,public_id):

        # making sure that only admins na query data from yhe database
    if not user_for_public_id.admin:
        return jsonify({"message":"cannot perfon above function! u are not admin"})

        
    single_user=User.query.filter_by(public_id=public_id).first()
    if not single_user:
        return jsonify({"message":" no user found! "})

    db.session.delete(single_user)
    db.session.commit()

    return jsonify({"message":"user deleted!"})

# login route
@app.route('/login')
def login():

    auth=request.authorization 
    if not auth or not auth.username or not auth.password:
        return make_response ('could not verify! nothing provided',401, {'WWW-Authenticate':'Basic realm="Login required!'})

    user = User.query.filter_by(name=auth.username).first()

    if not user:
        return make_response ('could not verify! username',401, {'WWW-Authenticate':'Basic realm="Login required!'})

    # to compare hasshed password yo use check_password_harsh
    # comparing text password to inputed password. if it is correct, we now generate the token

    if check_password_hash(user.password,auth.password):
        # creating token
        token = jwt.encode({"public_id": user.public_id, "exp":datetime.datetime.utcnow() + datetime.timedelta(minutes=30)}, app.config['SECRET_KEY'] )
        # returning the token as a jason object
        return jsonify({"token" : token.decode('UTF-8')})

    # if the password is wrong it returns the error message below
    return make_response ('could not verify! password ',401, {'WWW-Authenticate':'Basic realm="Login required!'})



# TODO routes

@app.route('/todo', methods=['GET'])
@token_required
def get_all_todo(user_for_public_id):
    """fetchng all todos"""
    all_todo= Todo.query.all()
    # creating empty list 
    todo_list=[]

    for todo in all_todo:
        # creating empty dict and adding items to it
        todo_dict={}
        todo_dict["todo_id"]=todo.id
        todo_dict["text"]=todo.text
        todo_dict["is complete"]=todo.complete
        todo_dict["user_id"]=todo.user_id
        # appending items tp the empty list
        todo_list.append(todo_dict)


    return jsonify({"message":todo_list})

@app.route('/todo/<todo_id>',methods=['GET'])
@token_required
def get_one_todo(user_for_public_id,todo_id):
    """getting one todo"""
    one_todo= Todo.query.filter_by(id=todo_id).first()
    if not one_todo:
        return jsonify({"message":"no todo found"})

    one_todo_dict = {}
    one_todo_dict["is complete"] = one_todo.complete
    one_todo_dict["text"]= one_todo.text
    one_todo_dict["user id"] = one_todo.text
    

    return jsonify({"response": one_todo_dict})


@app.route('/create_todo',methods=['POST'])
@token_required
def create_todo(user_for_public_id):
    """CREATING A NEW TODO"""
    data = request.get_json()
    
    new_data=Todo(text=data["text"],complete=False, user_id=user_for_public_id.id)
    db.session.add(new_data)
    db.session.commit()
    
    return jsonify({"message":data})


@app.route('/todo/<todo_id>',methods=['PUT'])
@token_required
def complete(user_for_public_id,todo_id):

    single_todo_complete=Todo.query.filter_by(id=todo_id).first()
    if not single_todo_complete:
        return jsonify({"message":"no todo found"})

    single_todo_complete.complete=True
    db.session.commit()
    

    return jsonify({"message":"todo complete!"})

@app.route('/todo/<todo_id>',methods=['DELETE'])
@token_required
def delete_todo(user_for_public_id,todo_id):

    todo_tobe_deleted= Todo.query.filter_by(id=todo_id).first()
    if not todo_tobe_deleted:
        return jsonify({"message":"no todo under that id!"})
    
    db.session.delete(todo_tobe_deleted)
    db.session.commit()

    return jsonify({"message":"todo deleted!"})









if __name__=='main':
    app.run(debug=True)