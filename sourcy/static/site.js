(function( $ ){

  $.fn.collapsify = function( options ) {  

    // Create some defaults, extending them with any options that were provided
    var settings = $.extend( {
      'head'         : 'h2,h3,h4',
      'group' : 'div'
    }, options);

    return this.each(function() {
        var targ = $(this);
        var sections = targ.children(settings.head).wrapInner('<a href="#"></a>');
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


  $.fn.tabify = function( options ) {  

    // Create some defaults, extending them with any options that were provided
    var settings = $.extend( {
      'foo'         : 'bar'
    }, options);

    return this.each(function() {
        var tabs = $(this).find('a');

        function activate_tab(t) {
            var active = $(t).attr('href');
            console.log(active);
            tabs.each(function() {
                var href= $(this).attr('href');
                if(href==active) {
                    $(this).parent().addClass('selected');
                    $(href).show();
                } else {
                    $(href).hide();
                    $(this).parent().removeClass('selected');
                }
            });
        }

        tabs.each(function() {
            console.log(this);
            $(this).click(function() {
                activate_tab($(this));
                return false;
            });
        });
        activate_tab($(tabs.get(0)));
        
    });

  };
})( jQuery );


