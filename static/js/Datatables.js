// Funcion que nos permite llenar el select subcategoria a partir
// Select categoria

const $categoria = $('#categoria')
const $subcategoria = $('#subcategoria')

$categoria.change(function(){
    $subcategoria.val('');
    $subcategoria.prop('disabled', !Boolean($categoria.val()));
    $subcategoria.find('option[data-region]').hide();
    $subcategoria.find('option[data-region="'+ $categoria.val() + '"]').show();
});

// Sidebar
$("#menu-toggle").click(function(e) {
    e.preventDefault();
    $("#wrapper").toggleClass("toggled");
 });
 $("#menu-toggle-2").click(function(e) {
    e.preventDefault();
    $("#wrapper").toggleClass("toggled-2");
    $('#menu ul').hide();
    
 });
 // Btn SweetArlet
 $('#btn_agregar').click(function(){
    Swal.fire({
        icon: 'success',
        title: 'Articulo ha sido guardado.',
        showConfirmButton: false,
        timer: 1500
      })
 });
 
 function initMenu() {
    $('#menu ul').hide();
    $('#menu ul').children('.current').parent().show();
 }
// Data Tables
$(document).ready( function () {
    $('#table_id').DataTable({
        autoFill: true,
        "language": {
            "lengthMenu": "Mostrar _MENU_ registros por página",
            "zeroRecords": "No se encontró nada - lo siento",
            "info": "Mostrando página _PAGE_ de _PAGES_",
            "infoEmpty": "No hay registros disponibles",
            "infoFiltered": "(filtrado de _MAX_ registros totales)",
            "sSearch": "Buscar:",
            "oPaginate":{
                "sFirst": "Primero",
                "sLast": "Ultimo",
                "sNext": "Siguiente",
                "sPrevious": "Anterior"
            },
            "sProcessing": "Procesando...",
        }
    });

    initMenu();
} );