from datetime import datetime, timedelta
import os
from flask import Flask, session, redirect, render_template, request, flash
from flask.helpers import url_for
from flask_session import Session
from sqlalchemy import create_engine
import sqlalchemy
from sqlalchemy.orm import scoped_session, sessionmaker
from flask_bcrypt import Bcrypt, check_password_hash,generate_password_hash
from helpers import login_required, rolAdmin_required, rolEmpleado_required, rolCliente_required
from Mail_routes import Mails
from flask_mail import Mail, Message
import uuid
from flask_paginate import Pagination, get_page_parameter

app = Flask(__name__)
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

# Set up database
engine = create_engine(os.getenv("DB_URL"))
db = scoped_session(sessionmaker(bind=engine))

ROWS_PER_PAGE = 10

# Funcion para obtener datos de la base de datos
def query():
    global categoria
    global subcategoria
    categoria = db.execute("select * from categoria").fetchall()
    subcategoria = db.execute("select * from subcategoria").fetchall()
 
# La duración predeterminada de la sesión es de 5 dias
@app.before_request
def set_session_timeout():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(days=5)

@app.route("/")
def index():

    # Paginacion
    page = request.args.get(get_page_parameter(), type=int, default=1)
    per_page = ROWS_PER_PAGE
    offset = (page - 1) * per_page
    main = db.execute("select * from producto left join marca on marca.id_marca = producto.id_marca ORDER BY RANDOM() LIMIT 10").fetchall()
    mains = main[offset:offset+per_page]
    pagination  = Pagination ( page = page, per_page = per_page, total=len(main), offset=offset, css_framework='bootstrap5' )
    
    # Obtenemos los datos de la funcion para mostrar en la pagina
    query()
    
    return render_template("index.html", 
                            main=mains,
                            page=page,
                            per_page=per_page,
                            pagination=pagination, 
                            categoria=categoria, 
                            subcategoria=subcategoria)

################################################ SISTEMA DE BUSQUEDA #############################################
@app.route("/busqueda", methods=["GET", "POST"])
def busqueda():
    # Metodo GET
    if request.method == 'GET':
        
        query()

        # Almacenamos en una variable el libro que deseamos buscar
        busqueda_values = request.args.get("Search_producto")

        # En caso del usuario ponga texto vacio retorne error
        if all(text.isspace() for text in busqueda_values):
            info_message = "😔 Hey! parece que no has puesto bien el producto que deseas buscar"
            flash(info_message, "info")
            return redirect("/")

        # Formateamos la datos recogido de busqueda_Values
        Busqueda = "%{}%".format(busqueda_values.strip())

        # Obtenemos los datos de la base de datos 
        B_producto = db.execute("SELECT producto.id_producto, producto.nombre, producto.precio_compra,producto.imagen, marca.nmarca, categoria.ncategoria ,subcategoria.nsubcategoria FROM producto LEFT JOIN Marca ON Marca.id_marca = producto.id_marca JOIN categoria ON categoria.id_categoria = producto.id_categoria JOIN subcategoria ON subcategoria.id_subcategoria = producto.id_subcategoria WHERE nombre ILIKE :n_producto OR nmarca ILIKE :n_marca OR ncategoria ILIKE :n_categoria OR nsubcategoria ILIKE :n_subcategoria", {"n_producto":Busqueda ,"n_marca":Busqueda ,"n_categoria":Busqueda ,"n_subcategoria":Busqueda}).fetchall() 
        
        
        # En caso de no encontrar producto en el inventario redirecionamos al error 404
        if not B_producto:
            return render_template("404.html", categoria=categoria, subcategoria=subcategoria), 404

        return render_template("Busqueda.html", main=B_producto, categoria=categoria, subcategoria=subcategoria)

################################################ DETALLE DE LOS PRODUCTO ##############################################
@app.route("/producto/detalle/"+str("<id_producto>"), methods=["POST", "GET"])
def producto(id_producto):
    # Metodo GET
    if request.method == 'GET':

        print("********************")
        print()
        print(id_producto)
        print()
        print("********************")
        # Obtenemos respectivamente los datos de cada uno.
        query()

        # Obtenemos datos de un producto especifico
        datos = db.execute("SELECT id_producto FROM producto WHERE nombre ILIKE :producto", {"producto":id_producto})
        id = datos.fetchone()[0]

        # Obtenemos los datos del producto seleccionado para mostrar los detalle
        producto = db.execute("SELECT producto.id_producto, producto.nombre, producto.descripcion, marca.nmarca, producto.stock, producto.precio_compra, subcategoria.nsubcategoria, producto.imagen, producto.imagen, producto.imagen FROM producto LEFT JOIN marca ON marca.id_marca = producto.id_marca JOIN subcategoria ON subcategoria.id_subcategoria = producto.id_subcategoria WHERE id_producto = :id_producto",{"id_producto": id}).fetchone()

        return render_template("detalle.html", producto=producto, categoria=categoria, subcategoria=subcategoria)
    else:
        return redirect('/Error/404')

################################################# SISTEMA DE LOGIN #################################################################
@app.route("/account/login", methods=["GET", "POST"])
def login():

    # Olvida cualquier id_user
    session.clear()
    Form_actual = "Login"
    # Metodo POST
    if request.method == 'POST':

        # Almacenamos en la variable los datos obtenido en el formulario
        email = request.form.get("email")
        password = request.form.get("password")

        rows = db.execute("SELECT * FROM usuario WHERE correo = :correo", {"correo":email}).fetchone()

        # Validacion del Usuario si existe en la base de datos 
        if db.execute("SELECT * FROM usuario WHERE correo = :correo", {"correo":email}).rowcount == 0:
            error_message = "😕 Hey! parece que tuvimos un problema con tu email"
            flash(error_message, "alert-danger")
            return render_template("account/Formulario.html", Form_actual = Form_actual) 

        # Validacion de la contraseña al iniciar sesion
        if not check_password_hash(rows[6], password):
            error_message = "😕 Hey! parece que tuvimos un problema con tu contraseña"
            flash(error_message, "alert-danger")
            return render_template("account/Formulario.html", Form_actual = Form_actual)

        # Validacion si la cuenta esta activado
        if  rows[8] == False:
            error_message = "😕 Hey! parece que no has activado tu cuenta"
            flash(error_message, "alert-danger")
            return render_template("account/Formulario.html", Form_actual = Form_actual)

        # Guardamos datos especifico en la session
        session["id_usuario"] = rows[0]
        session['nombre'] = rows[1]
        print("***********************************************")
        print()
        print(session["id_usuario"])
        print(session["nombre"])
        if rows[9] == 1:
            session['Empleado'] = rows[9]
            print(session['Empleado'], "Session Empleado")
        elif rows[9] == 2:
            session['Administrador'] = rows[9]
            session['Empleado'] = rows[9]
            print(session['Empleado'], "Session Empleado")
            print(session['Administrador'] , "Session Administrador")
        else:
            session['Cliente'] = rows[9]
            print(session['Cliente'], "Session Cliente")  
        print()
        print("***********************************************")
        # Redirecionamos a la pagina principal
        return redirect("/")
    else:
        return render_template("account/Formulario.html", Form_actual = Form_actual)

################################################ SISTEMA DE REGISTRO ###########################################
@app.route("/account/register", methods=["GET", "POST"])
def register():

    # Olvida cualquier id_user
    session.clear()

    # Metodo POST
    if request.method == 'POST':

        # Almacenamos en la variable los datos obtenido en el formulario
        nombre = request.form.get("Nombre").strip()
        apellido = request.form.get("Apellido").strip()
        correo = request.form.get("email").strip()
        password = request.form.get("password").strip()
        checkpassword = request.form.get("checkpassword").strip()
        activado = False
        # Validamos en la base de datos de que no haya otro usuario con el mismo correo
        if db.execute("SELECT * FROM usuario WHERE correo = :correo", {"correo":correo}).rowcount == 1:
            error_message = "😕 Hey!, este correo ya fue registrado"
            flash(error_message, "alert-info")
            return render_template("account/Formulario.html")

        # Chequeamos si la contraseña son iguales
        if password != checkpassword:
            error_message = "😕 Hey! parece que tuvimos un problema con tu verificacion de contraseña vuelve a intentar"
            flash(error_message, "alert-info")
            return render_template("account/Formulario.html")
        
        # Validamos de que no guarde el nombre del usuario y contraseña con espacios
        elif all(text.isspace() for text in nombre):
            info_message = "😕 Hey! parece que no has puesto bien el nombre de usuario"
            flash(info_message, "alert-info")
            return render_template("account/Formulario.html")

        elif all(text.isspace() for text in password):
            info_message = "😕 Hey! parece que no has puesto bien la contraseña"
            flash(info_message, "alert-info")
            return render_template("account/Formulario.html")

        elif all(text.isspace() for text in correo):
            info_message = "😕 Hey! parece que no has puesto bien el correo"
            flash(info_message, "alert-info")
            return render_template("account/Formulario.html")
        # Encriptamos la contraseña y decodificamos la cadena
        hash = generate_password_hash(password).decode('utf-8')

        # Ingresamos los datos en la base de datos
        db.execute("INSERT INTO usuario (nombre, apellido, correo, contraseña, activado, roles) VALUES (:nombre, :apellido, :correo, :contraseña, :activado, :roles)", {"nombre":nombre, "apellido":apellido, "correo":correo, "contraseña":hash, "activado":activado,"roles":3})
        db.commit()

        token = str(uuid.uuid4())
        msg = Message(subject='Activacion de cuenta', sender=app.config['MAIL_USERNAME'], recipients=[correo])
        msg.body = render_template("mail/Activador.html", token=token).encode("utf-8")  
        mail.send(msg)
        db.execute("UPDATE usuario SET token = :token WHERE correo= :correo", {"token":token,"correo":correo})
        db.commit()
        db.close()
        success_message = "😀 Hey! hemos enviado un correo de activacion a tu bandeja"
        flash(success_message, "alert-success")
        # Redirecionamos a la pagina principal
        return render_template("account/Formulario.html", Form_actual = "Login")
    else:
        # En caso de falla volvemos a cargar la pagina registro
        return render_template("account/Formulario.html")

# Logout
@app.route("/account/logout")
def logout():

    # Olvida cualquier id_user
    session.clear()

    # Redirecionamos al usuario a la pagina index
    return redirect("/")

@app.route("/subcategoria/"+str("<id_subcategoria>"), methods=["POST", "GET"])
def subcategory(id_subcategoria):
    # METODO GET
    if request.method == 'GET':
        # Recogemos los datos de la base de datos 
        query()

        # Obtenemos datos de un producto especifico
        datos = db.execute("SELECT id_subcategoria FROM subcategoria WHERE nsubcategoria = :subcategoria", {"subcategoria":id_subcategoria})
        id = datos.fetchone()[0]

        # Obtenemos los datos de la base de datos 
        B_SubCategory = db.execute("SELECT producto.id_producto, producto.nombre, producto.id_subcategoria, producto.precio_compra, producto.imagen,producto, marca.nmarca, categoria.ncategoria ,subcategoria.nsubcategoria FROM producto LEFT JOIN marca ON marca.id_marca = producto.id_marca JOIN categoria ON categoria.id_categoria = producto.id_categoria JOIN subcategoria ON subcategoria.id_subcategoria = producto.id_subcategoria WHERE producto.id_subcategoria = :id_subcategoria ", {"id_subcategoria":id}).fetchall()

        # En caso de no encontrar producto en el inventario redirecionamos al error 404
        if not B_SubCategory:
            return redirect('/Error/404')

        return render_template("Busqueda.html", main=B_SubCategory, categoria=categoria, subcategoria=subcategoria)

############################# SISTEMA DE CARRITO DE COMPRAS ##########################################
#Detalle Carrito
@app.route("/carrito/detalle", methods=["POST", "GET"])
@login_required
def detail_cart():
    query()
    pedido = db.execute("SELECT * FROM carrito LEFT JOIN producto ON producto.id_producto = carrito.id_producto WHERE carrito.id_usuario = :user",{"user": session["id_usuario"]}).fetchall()
    print(pedido)
    return render_template("Cart/cart_detail.html",pedido=pedido,categoria=categoria, subcategoria=subcategoria)

@app.route("/add/cart/"+str("<id_producto>"), methods=["POST","GET"])
@login_required
def cart(id_producto):

    if request.method == 'GET':
        
        pro = db.execute("SELECT * FROM producto WHERE id_producto = :producto_id", {"producto_id": id_producto}).fetchone()
        id = pro[0]
        cantidad = 1
        
        print("******************************************************")
        print("")
        print("ITEMS---------------------", id)
        
        print("Precio-------------------", pro[7])
        print("")
        print("")
        print("*****************************************************")
        db.execute("INSERT INTO carrito (id_usuario, id_producto, precio_unidad, cantidad, fecha) VALUES (:id_usuario, :id_producto, :precio, :cantidad, :fecha)", {"id_usuario":session['id_usuario'],"id_producto":id,"precio":pro[7], "cantidad":cantidad, "fecha":datetime.now()})
        db.commit()
    
    return redirect("/producto/detalle/"+str(pro[4]))
    
@app.route("/confirm/cart/<id_producto>", methods=["POST","GET"])
@login_required
def conf_cart(id_producto):

    if request.method == 'POST':

        db.execute("UPDATE carrito SET confirmar = :conf WHERE id_carrito = :id_producto",{"conf":True,"id_producto":id_producto})
        db.commit()
    return redirect("/carrito/detalle")

@app.route("/delete/cart/<id_producto>", methods=["POST","GET"])
@login_required
def delete_cart(id_producto):
    if request.method == 'POST':

        # Eliminamos el producto del carrito
        db.execute("DELETE FROM carrito WHERE id_carrito = :id_producto", {"id_producto":id_producto})
        db.commit()

    return redirect("/carrito/detalle")

@login_required
@app.route("/historial/carrito", methods=["POST", "GET"])
def historial_cart():
    query()
    
    pedido = db.execute("SELECT * FROM carrito LEFT JOIN producto ON producto.id_producto = carrito.id_producto WHERE carrito.id_usuario = :user",{"user": session["id_usuario"]}).fetchall()
    print(pedido)
    return render_template("Cart/historial.html",pedido=pedido,categoria=categoria, subcategoria=subcategoria)

####################### LISTA DE DESEO ###################################################
@app.route("/add/deseos", methods=["POST", "GET"])
@login_required
def lista():
    # METODO POST
    print("----------------------FUNCIONA AGREGAR DESEOS?----------------------------")
    if request.method == 'GET':
        id_produc = request.args.get("id")
        print("------------------ENTRE A GET-------------------------")
        # Obtenemos datos de un producto especifico
        datos = db.execute("SELECT * FROM producto WHERE id_producto = :producto", {"producto":id_produc})
        id = datos.fetchone()[0]
        user=session['id_usuario']
        db.execute("INSERT INTO lista_deseo (id_usuario, id_producto, agregado) VALUES (:user_id, :producto_id, :agregado)", {"user_id":user, "producto_id":id, "agregado":True})
        db.commit()
    return redirect('/')

@app.route("/delete/deseos", methods=["POST", "GET"])
@login_required
def Dlista():
    # METODO POST
    print("----------------------FUNCIONA BORRAR DESEOS?----------------------------")
    if request.method == 'GET':
        id_produc = request.args.get("id")
        # Obtenemos datos de un producto especifico
        lista = db.execute("SELECT * FROM lista_deseo WHERE id_producto = :producto", {"producto":id_produc})
        id = lista.fetchone()[1]
        user=session['id_usuario']
        db.execute("DELETE FROM lista_deseo WHERE id_usuario = :user_id AND id_producto = :producto_id ", {"user_id":user, "producto_id":id})
        db.commit()
        print("------------------Borrado con exito-------------------------", id)
    return redirect('/')
    

@app.route("/lista/deseos", methods=["POST", "GET"])
@login_required
def añadir_deseo():
    # Obtenemos respectivamente los datos de cada uno.
    query()
    deseo = db.execute("Select * from lista_deseo LEFT JOIN producto ON producto.id_producto = lista_deseo.id_producto JOIN marca on marca.id_marca = producto.id_marca WHERE lista_deseo.id_usuario = :user",{"user":session['id_usuario']})

    return render_template("deseo.html", main=deseo, categoria=categoria, subcategoria=subcategoria)

# EMPIEZA EL CRUD - SISTEMA DE INVENTARIO
@app.route("/Administracion/Sistema_de_inventario", methods=["POST", "GET"])
@login_required
@rolEmpleado_required
def Sistema():
    # Paginacion
    page = request.args.get(get_page_parameter(), type=int, default=1)
    per_page = ROWS_PER_PAGE
    offset = (page - 1) * per_page
    # Recogemos los datos de todos los producto que se encuentra en la base de datos
    data= db.execute("SELECT *,substring(descripcion::text, 1,100) as descripciont FROM producto LEFT JOIN marca ON marca.id_marca = producto.id_marca JOIN subcategoria ON subcategoria.id_subcategoria = producto.id_subcategoria JOIN categoria ON categoria.id_categoria = producto.id_categoria ORDER BY id_producto ASC").fetchall()
    datas = data[offset:offset+per_page]
    pagination  = Pagination ( page = page, per_page = per_page, total=len(data), offset=offset, css_framework='bootstrap5' )

    data1 = db.execute("SELECT * from categoria").fetchall()
    data2 = db.execute("SELECT * FROM marca").fetchall()
    data3 = db.execute("SELECT * from subcategoria").fetchall()

    return render_template("Sistema/Control_Crud.html", 
                            Datos=datas, 
                            data1=data1, 
                            data2=data2, 
                            data3=data3, 
                            page=page,
                            per_page=per_page,
                            pagination=pagination)

# Agregar nuevos producto al inventario
@app.route("/Administrador/Sistema_de_inventario/agregar", methods=["POST", "GET"])
@login_required
@rolEmpleado_required
def agregar():
    
    # METODO POST
    print("FUNCIONA EL BOTON DE AGREGAR")
    if request.method == 'POST':
        # Recogemos los datos especifico para agregar nuevo datos
        Nproducto = request.form.get("Nproducto").strip()
        descripcion = request.form.get("descripcion").strip()
        categoria = request.form.get("categoria")
        subcategoria = request.form.get("subcategoria")
        fabricante = request.form.get("fabricante")
        stock = request.form.get("stock")
        precio = request.form.get("precio")
        print("ENTRE AL METODO POST-----------------", subcategoria)

        # Agregamos nuevos producto en la base de datos
        db.execute("INSERT INTO producto (nombre, descripcion, id_categoria, id_subcategoria, id_marca, stock, precio_compra) VALUES (:n_producto, :descripcion, :categoria_id, :subcategoria_id, :id_marca, :stock, :precio )", {"n_producto":Nproducto, "descripcion":descripcion, "categoria_id":categoria, "subcategoria_id":subcategoria, "id_marca":fabricante, "stock":stock, "precio":precio})
        db.commit()
    
    return redirect('/Administrador/Sistema_de_inventario')

# Borrar Datos del inventario
@app.route("/Administrador/Sistema_de_inventario/delete/<id_producto>", methods=["POST", "GET"])
@login_required
@rolEmpleado_required
def borrar(id_producto):

    # Metodo POST
    if request.method == 'POST':

        # Eliminamos el producto en la base de datos
        db.execute("DELETE FROM producto WHERE id_producto = :id_producto", {"id_producto":id_producto})
        db.commit()

    return redirect('/Administrador/Sistema_de_inventario')

# Actualizar datos del inventarios
@app.route("/Administrador/Sistema_de_inventario/editar/<id_producto>", methods=["POST", "GET"])
@login_required
@rolEmpleado_required
def editar(id_producto):
    if request.method == 'POST':

        # Recogemos los datos para actualizar los datos de la base de datos
        Nproducto = request.form.get("Nproducto").strip()
        descripcion = request.form.get("descripcion").strip()
        img1 = request.form.get("URLimg1").strip()
        #img2 = request.form.get("URLimg2").strip()
        #img3 = request.form.get("URLimg3").strip()
        stock = request.form.get("stock")
        precio = request.form.get("precio")
        #urlproducto = request.form.get("URLproduc")

        # Actualizamos los datos en la base de datos
        db.execute("UPDATE producto SET nombre = :n_producto , descripcion = :descripciones, stock = :stock , precio_compra = :precio, imagen = :img1 WHERE id_producto = :id_producto", {"n_producto":Nproducto, "descripciones":descripcion, "stock":stock, "precio":precio,"img1":img1, "id_producto":id_producto})
        db.commit()

    return redirect('/Administrador/Sistema_de_inventario')

############################### Administracion de Cliente ###############################
@app.route("/Administracion/Cliente", methods=["POST", "GET"])
@login_required
@rolEmpleado_required
def Cliente():
    # Paginacion
    page = request.args.get(get_page_parameter(), type=int, default=1)
    per_page = ROWS_PER_PAGE
    offset = (page - 1) * per_page
    Cliente = db.execute("Select * from usuario").fetchall()
    Clientes = Cliente[offset:offset+per_page]
    pagination  = Pagination ( page = page, per_page = per_page, total=len(Cliente), offset=offset, css_framework='bootstrap5' )
    return render_template("/Sistema/Usuarios_Crud.html", 
                            Cliente=Clientes,
                            page=page,
                            per_page=per_page,
                            pagination=pagination)

@app.route("/Administracion/agregar/cliente", methods=["POST", "GET"])
@login_required
@rolEmpleado_required
def addCliente():
    
    if request.method == 'POST':

        # Almacenamos en la variable los datos obtenido en el formulario
        nombre = request.form.get("Nombre").strip()
        apellido = request.form.get("Apellido").strip()
        correo = request.form.get("Correo").strip()
        password = request.form.get("password").strip()
        telefono = request.form.get("Telefono").strip()
        cedula = request.form.get("Cedula").strip()
        Rol = request.form.get("Rol").strip()

        # Validamos en la base de datos de que no haya otro usuario con el mismo correo
        if db.execute("SELECT * FROM usuario WHERE correo = :correo", {"correo":correo}).rowcount == 1:
            error_message = "😕 Hey!, este correo ya fue registrado"
            flash(error_message, "alert-info")
            return redirect('/Administracion/Cliente')

        if len(telefono) > 8:

            error_message = "😕 Hey!, Vuelve a intentar pero con menos digitos"
            flash(error_message, "alert-info")
            return redirect('/Administracion/Cliente')

        if len(cedula) > 16:

            error_message = "😕 Hey!, Vuelve a intentar pero de esta manera 001-000000-0000U"
            flash(error_message, "alert-info")
            return redirect('/Administracion/Cliente')

        # Chequeamos si la contraseña son iguales
        
        # Validamos de que no guarde el nombre del usuario y contraseña con espacios
        elif all(text.isspace() for text in nombre):
            info_message = "😕 Hey! parece que no has puesto bien el nombre de usuario"
            flash(info_message, "alert-info")
            return redirect('/Administracion/Cliente')

        elif all(text.isspace() for text in password):
            info_message = "😕 Hey! parece que no has puesto bien la contraseña"
            flash(info_message, "alert-info")
            return redirect('/Administracion/Cliente')

        elif all(text.isspace() for text in correo):
            info_message = "😕 Hey! parece que no has puesto bien el correo"
            flash(info_message, "alert-info")
            return redirect('/Administracion/Cliente')
        # Encriptamos la contraseña y decodificamos la cadena
        hash = generate_password_hash(password).decode('utf-8')

        # Ingresamos los datos en la base de datos
        db.execute("INSERT INTO usuario (nombre, apellido, correo, telefono, cedula, contraseña, activar, roles) VALUES (:nombre, :apellido, :correo, :telefono, :cedula, :contraseña, :activacion,:roles)", {"nombre":nombre, "apellido":apellido, "correo":correo, "telefono":telefono, "cedula":cedula, "contraseña":hash, "activacion":True,"roles":Rol})
        db.commit()
        
        # Redirecionamos a la pagina principal
        return redirect('/Administracion/Cliente')
        
    else:
        # En caso de falla volvemos a cargar la pagina
        return redirect('/Administracion/Cliente')

@app.route("/Administracion/delete/cliente/<id_usuario>", methods=["POST", "GET"])
@login_required
@rolEmpleado_required
def Clientedelete(id_usuario):

    if request.method == 'POST':

        # Eliminamos el usuario en la base de datos
        db.execute("DELETE FROM usuario WHERE id_usuario = :id_usuario", {"id_usuario":id_usuario})
        db.commit()


    return redirect('/Administracion/Cliente')

@app.route("/Administracion/update/cliente/<id_usuario>", methods=["POST", "GET"])
@login_required
@rolEmpleado_required
def Clienteupdate(id_usuario):

    if request.method == 'POST':

    
        Nombre = request.form.get("NombreU").strip()
        Apellido = request.form.get("Apellido").strip()
        Correo = request.form.get("Correo").strip()
        Telefono = request.form.get("Telefono").strip()
        Cedula = request.form.get("Cedula").strip()
        Rol = request.form.get("Rol").strip()
        
        if len(Telefono) > 8:

            error_message = "😕 Hey!, Vuelve a intentar pero con menos digitos"
            flash(error_message, "alert-info")
            return redirect('/Administrador/Cliente')

        if len(Cedula) > 16:

            error_message = "😕 Hey!, Vuelve a intentar pero de esta manera 001-000000-0000U"
            flash(error_message, "alert-info")
            return redirect('/Administrador/Cliente')

        db.execute("UPDATE usuario SET nombre = :Nombre , apellido = :Apellido, correo = :Correo , telefono = :Telefono, cedula = :Cedula, roles = :Rol WHERE id_usuario = :id_usuario", {"id_usuario":id_usuario, "Nombre":Nombre, "Apellido":Apellido, "Correo":Correo, "Telefono":Telefono, "Cedula":Cedula, "Rol":Rol})
        db.commit()

        error_message = "😀 Hey!, hemos actualizado los datos"
        flash(error_message, "alert-info")

    return redirect('/Administracion/Cliente')


################################## ERROR 404 #################################################
@app.errorhandler(404)
def not_found(e):
    
    # Recogemos los datos de la funcion Def
    query()
    return render_template("404.html", categoria=categoria, subcategoria=subcategoria), 404

# Modulo de Mail.routes.py
app.register_blueprint(Mails)

if __name__ == "__main__":
    app.run(debug=True)
    bcrypt = Bcrypt(app)