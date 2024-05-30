from turtle import delay
from flask_mail import Mail, Message
import flask
import uuid
from application import *

app = Flask(__name__)
Mails = flask.Blueprint('Mails', __name__)

# Check for environment variable
if not os.getenv("DB_URL"):
    raise RuntimeError("DB_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 25
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv("MAIL_USER")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")
mail = Mail(app)

engine = create_engine(os.getenv("DB_URL"))
db = scoped_session(sessionmaker(bind=engine))


@Mails.route('/forgotpassword', methods = ['GET', 'POST'])
def forgot():    
    Form_actual = "Reset"
    if request.method == 'POST':

        correo = request.form.get('correo')
        token = str(uuid.uuid4())
        rows = db.execute("SELECT * FROM usuario WHERE correo = :correo", {"correo":correo}).fetchone()
        print("**********************")
        print()
        print(os.environ.get('MAIL_PASSWORD'))
        print()
        print("**********************")

        if db.execute("SELECT * FROM usuario WHERE correo = :correo", {"correo":correo}).rowcount == 1:

            msg = Message(subject='Solicitud de contraseña olvidada', sender=app.config['MAIL_USERNAME'], recipients=[correo])
            msg.body = render_template("mail/sent.html", token=token, rows=rows).encode("utf-8")
            
            mail.send(msg)
            print(msg)
            print(rows.correo)
            db.execute("UPDATE usuario SET token = :token WHERE correo= :correo", {"token":token,"correo":correo})
            db.commit()
            db.close()
            flash("Correo enviado", 'success')
            return render_template('mail/forgot.html')
        else:
            flash("Tenemos problema con tus datos", 'danger')

    return render_template('mail/forgot.html', Form_actual = Form_actual)

@Mails.route('/reset/<token>', methods = ['GET', 'POST'])
def reset(token):

    if request.method == "POST":

        password = request.form.get("password").strip()
        checkpassword = request.form.get("checkpassword").strip()
        new_token = str(uuid.uuid4())

        print("**********************")
        print(password)
        print(token)
        print()
        print("**********************")

        if password != checkpassword:
            flash("las nuevas contraseña que ingreso no coinciden!")
            return redirect('/reset/'+str(token))
            
        # Encriptamos la contraseña y decodificamos la cadena
        hash = generate_password_hash(password).decode('utf-8')
        user = db.execute("SELECT * FROM usuario WHERE token = :token", {"token":token}).fetchone()
        if user:
            db.execute("UPDATE usuario SET token = :token1, contraseña = :password WHERE token = :token",{"token1":new_token, "password":hash, "token":token})
            db.commit()
            db.close()
            flash("Su contraseña ha sido actualizado", 'success')
            session.clear()
            return redirect('/account/login')
        else:
            flash("Tu token es invalido", 'danger')
            return redirect('/forgotpassword')
    return render_template('mail/reset.html', token=token)

@Mails.route('/activar/<token>', methods = ['GET', 'POST'])
def activar(token):

    if request.method == "GET":

        activado = True
        new_token = str(uuid.uuid4())

        print("**********************")
        print()
        print(token)
        print()
        print("**********************")
        user = db.execute("SELECT * FROM usuario WHERE token = :token", {"token":token}).fetchone()
        if user:
            db.execute("UPDATE usuario SET token = :token1, activado = :activar WHERE token = :token",{"token1":new_token,"token":token, "activar": activado})
            db.commit()
            db.close()
            session.clear()
            success_message = "😀 Hey! hemos activado tu cuenta correctamente"
            flash(success_message, "alert-success")
            return render_template("account/Formulario.html", Form_actual = "Login")
        else:
            flash("Tu token es invalido", 'danger')
            return redirect('/account/login')
    return render_template("account/Formulario.html")