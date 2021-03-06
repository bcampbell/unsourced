
(function( $ ){

  // escape special regex chars
  $.reescape = function(str) {
    var specials = new RegExp("[.*+?|()\\[\\]{}\\\\]", "g"); // .*+?|()[]{}\
    return str.replace(specials, "\\$&");
  };

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



  /* turn a set of links into tabs. href gives content element for each tab */
  $.fn.tabify = function( options ) {  
    var settings = $.extend( {
      'activeClass'         : 'is-active'
    }, options);

    var targs = this.map(function() {
      var targ = $(this).attr('href');
      return $(targ)[0];
    });
    var buttons = $(this);

    var clicked = function(a) {
       buttons.removeClass(settings.activeClass);
       $(a).addClass(settings.activeClass);

       $(targs).hide();
       var targ = $(a).attr('href');
       $(targ).show();
    };

    clicked(this[0]);

    return this.each(function() {
      $(this).click(function() {
        clicked($(this)[0]);
        return false;
      });
    });
/*
        var tabs = $(this).find('a');

        function activate_tab(t) {
            var active = $(t).attr('href');
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
            $(this).click(function() {
                activate_tab($(this));
                return false;
            });
        });
        activate_tab($(tabs.get(0)));
        
    });
*/
  };


  // convert daily breakdown table into a chart
  $.fn.dailychart = function( options ) {
    var settings = $.extend( {
      'foo'         : 'bar'
    }, options);


    function table_to_data(src) {
        var rows = [];
        $('tbody tr', src).each(function(i, tr) {
            var row = [];
            $('th,td',tr).each(function(i,td) {
                row.push($(td).html());
            });
            rows.push(row);
        });
        return rows;
    }


    return this.each(function() {
        var data = table_to_data($(this));

        $(this).hide();

        var rows = [];
        $(data).each( function(i,d) {
            var percent = 0.0;
            if(d[2] > 0) {
                percent = d[1] / d[2];
            }
            rows.push('<span>'+d[0]+'</span><div class="graph"><span class="bar" style="width:'+percent+'%;">'+percent+'%</span></div>\n');
        });
        $(this).after('<div style="clear:both;">' + rows.join('')+"</div>");


    });
  };

})( jQuery );



pubsub = {
  source_added: $.Callbacks()
};



function showFormErrs(form,errs) {

  // clear out any previous messages
  form.find('.error').removeClass('error');
  form.find('.errorlist').empty();

  for( var fieldname in errs ) {
    field_container = form.find('#'+fieldname).parent()
    errlist = field_container.find('.errorlist')
    if(errlist.length==0) {
      errlist = form.find('.errorlist');
    }

    for( var msg in errs[fieldname] ) {
      errlist.append('<li>' + errs[fieldname][msg] + '</li>');
    }
    field_container.addClass('error');
  }
}


function ajaxifyAddSourceForm(form, busytext) {
  form.submit( function(e){
    e.preventDefault();

    var form = $(this);
    var url = form.attr('action');
    var params = form.serialize();

    // clear off any old errors
    form.find('.error').removeClass('error');
    form.find('.errorlist>*').remove();

    form.addClass('is-busy');
    form.find('.busy-message').html(busytext);
    $.ajax({
      type: "POST",
      url: url,
      data: params,
      complete: function(jqXHR, textStatus) {
        form.removeClass('is-busy');
        form.find('.busy-message').html("");
      },
      error: function(jqXHR, textStatus, errorThrown) {
      },
      success: function(data){
        if(!data.success){
          showFormErrs(form, data.errors);
        } else {
          // hide the form and show the newly-added item
          pubsub.source_added.fire(data.new_source);
          form.each( function() { this.reset(); });
        }
      }
    });
  });
}


