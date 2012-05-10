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


  $.fn.tabify = function( options ) {  

    // Create some defaults, extending them with any options that were provided
    var settings = $.extend( {
      'foo'         : 'bar'
    }, options);

    return this.each(function() {
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

  };


  /* convert daily breakdown table into a chart */
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




function showFormErrs(form,errs) {

  // clear out any previous messages
  form.find('.error').removeClass('error');
  form.find('.errorlist').remove();

  for( var field in errs ) {
    var html = '<ul class="errorlist">';
    for( var msg in errs[field] ) {
      html += '<li>' + errs[field][msg] + '</li>';
    }
    html += '</ul>';
    form.find('#'+field).after(html);
    form.find('#'+field).parent().addClass('error');
  }
}


