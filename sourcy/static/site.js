(function( $ ){

  $.fn.collapsify = function( options ) {  

    // Create some defaults, extending them with any options that were provided
    var settings = $.extend( {
      'head'         : 'h2',
      'group' : 'div'
    }, options);

    return this.each(function() {
        var targ = $(this);
        var sections = targ.find(settings.head).wrapInner('<a href="#"></a>');
        $(sections).each( function() {
            var grp = $(this).next(settings.group);

            $(this).removeClass('active');
            $(this).addClass('inactive');
            grp.hide();

            $(this).click( function() {
                if(grp.is(":visible")) {
                    $(this).removeClass('active');
                    $(this).addClass('inactive');
                    grp.hide();
                } else {
                    $(this).addClass('active');
                    $(this).removeClass('inactive');
                    grp.show();
                }
                return false; });
        });
    });

  };
})( jQuery );


