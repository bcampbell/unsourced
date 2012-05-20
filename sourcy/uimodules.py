import urllib   # for urlencode
from pprint import pprint
import datetime

import tornado.web

from models import Source,SourceKind,Article,Action
import util


source_presentation = {
    SourceKind.PAPER: {'icon':'paper_icon.png', 'desc':'Academic paper'},
    SourceKind.PR: {'icon':'recycle_icon.png', 'desc':'Press release'},
    SourceKind.OTHER: {'icon':'chain_icon.png', 'desc':'Other link'},
    }


class formfield(tornado.web.UIModule):
    def render(self, field):
        return self.render_string("modules/formfield.html", field=field)


class form(tornado.web.UIModule):
    def render(self, form):
        return self.render_string("modules/form.html", form=form)



class domain(tornado.web.UIModule):
    def render(self, url):
        return util.domain(url)


class day_overview(tornado.web.UIModule):
    def render(self, date, arts):
        num_sourced = sum((1 for a in arts if len(a.sources)>0))
        return self.render_string("modules/day_overview.html", date=date, arts=arts, num_sourced=num_sourced)


class user(tornado.web.UIModule):
    def render(self, user, show_avi):
        out = u''
        if show_avi:
            out += user.photo_img('s')

        if user is not None:
            out += u'<a href="/user/%d">%s</a>' % (user.id, user.username)
        else:
            out += u'anonymous'
        return out

class art_link(tornado.web.UIModule):
    def render(self, art):
        return '<a href="/art/%s">%s</a> (%s)' % (art.id, art.headline, util.domain(art.permalink))









class source(tornado.web.UIModule):
    def render(self, src, container='div'):

        can_upvote = False
        can_downvote = False
        if self.current_user is not None:
            prev_vote = self.handler.session.query(Action).filter_by(what='src_vote',user_id=self.current_user.id, source=src).first()

            if prev_vote is None or prev_vote.value>0:
                can_downvote = True
            if prev_vote is None or prev_vote.value<0:
                can_upvote = True

        return self.render_string("modules/source.html",
            src=src,
            can_upvote=can_upvote,
            can_downvote=can_downvote,
            container=container,
            kind_desc=source_presentation[src.kind]['desc'],
            kind_icon='/static/' + source_presentation[src.kind]['icon'])


class art_item(tornado.web.UIModule):
    """ handle an article as an entry in a list - ie one line with title, link etc... """
    def render(self, art, show_pubdate=False, show_icons=True):
        return self.render_string("modules/art_item.html",
            art=art, show_pubdate=show_pubdate, show_icons=show_icons)

class action(tornado.web.UIModule):
    """ describe an action """
    def render(self, act, show_article=True, show_full_source=True, user_display='m' ):

        desc = u''

        art = act.article
        if art:
            artlink = u'<a href="%s">%s</a>' % (art.art_url(), art.headline)

        src_kinds = {
            SourceKind.PAPER: u'a paper',
            SourceKind.PR: u'a press release',
            SourceKind.OTHER: u'a link' }

        if not show_article:
            # article point of view - show without article link
            if act.what == 'src_add':
                desc = u"added %s" % (src_kinds[act.source.kind],)
            elif act.what == 'src_remove':
                desc = u"removed a source from %s" % (artlink,)
            elif act.what =='art_add':
                desc = u'submitted'
            elif act.what =='comment':
                desc = u'said "%s"' % (act.comment.format(),)
#            elif act.what =='tag_add':
#                desc = u'said "%s"' % (act.comment.content,)
        else:
            if act.what == 'src_add':
                desc = u"added %s to %s" % (src_kinds[act.source.kind], artlink)
            elif act.what == 'src_remove':
                desc = u"removed a source from %s" % (artlink,)
            elif act.what =='art_add':
                desc = u'submitted article: %s' % (artlink,)
            elif act.what =='comment':
                desc = u'said "%s" on %s' % (act.comment.format(), artlink)
#            elif act.what =='tag_add':
#                desc = u'said "%s" on %s' % (act.comment.content, artlink)

        return self.render_string("modules/action.html",
            act=act,
            show_article=show_article,
            show_full_source=show_full_source,
            desc_html=desc,
            user_display=user_display
        )



class daily(tornado.web.UIModule):
    def render(self,day,row):
        return self.render_string("modules/daily.html",
            day=day,row=row)

class source_icon(tornado.web.UIModule):
    """ iconic representation of a source """
    def render(self,src):
        kind_icon = '/static/' + source_presentation[src.kind]['icon']
        kind_desc = source_presentation[src.kind]['desc']
        return """<img src="%s" title="%s"/>""" % (kind_icon,kind_desc)


class league_table(tornado.web.UIModule):
    def render(self, rows, heading, action_desc):
        return self.render_string('modules/league_table.html',rows=rows, heading=heading, action_desc=action_desc)




class tool_googlescholar(tornado.web.UIModule):
    def render(self, institutions, journals, researchers):
        return self.render_string('modules/tool_googlescholar.html',
            institutions=institutions,
            journals=journals,
            researchers=researchers)


    def embedded_javascript(self):
        return """
    $('.help form .researcher').each(function(index) {
        var fullname = '"' + $.trim($(this).text()) + '"';

        var cb = $('<input type="checkbox" />').change(function() {
            var cur = $.trim($('#as_sauthors').val());
            var pat = new RegExp($.reescape(fullname),"ig");
            if(this.checked) {
               cur = cur + " " + fullname;
            } else {
               cur = cur.replace(pat,'');
            }
            $('#as_sauthors').val(cur);
        });
        cb.prependTo(this);
        $(this).wrap("<label/>");
    });

    $('.help form .journal').each(function(index) {
        var fullname = $.trim($(this).text()); 

        var cb = $('<input type="radio" name="j"/>').change(function() {
            var cur = $.trim($('#as_publication').val());
            var pat = new RegExp($.reescape(fullname),"ig");
            if(this.checked) {
               cur = fullname;
            } else {
               cur = cur.replace(pat,'');
            }
            $('#as_publication').val(cur);
        });
        cb.prependTo(this);
        $(this).wrap("<label/>");

    });

        """


class add_paper(tornado.web.UIModule):
    def render(self, art, add_paper_form):
        return self.render_string('modules/add_paper.html', art=art, form=add_paper_form)

    def embedded_javascript(self):
        return """
            ajaxifyAddSourceForm(
                $('#add-paper'),
                "Looking up details...",
                $('.sources .list-paper'));
        """


class add_pr(tornado.web.UIModule):
    def render(self, art, add_pr_form):
        return self.render_string('modules/add_pr.html', art=art, form=add_pr_form)

    def embedded_javascript(self):
        return """
            ajaxifyAddSourceForm(
                $('#add-pr'),
                "Adding...",
                $('.sources .list-pr'));
        """



class add_other(tornado.web.UIModule):
    def render(self, art, add_other_form):
        return self.render_string('modules/add_other.html', art=art, form=add_other_form)

    def embedded_javascript(self):
        return """
            ajaxifyAddSourceForm(
                $('#add-other'),
                "Adding...",
                $('.sources .list-other'));
        """




class login(tornado.web.UIModule):
    def render(self, form):
        reg_url = '/register'
        try:
            next = form.next.data
            if next is not None:
                reg_url += "?" + urllib.urlencode({'next':next})
        except AttributeError:
            pass
        return self.render_string('modules/login.html', form=form, reg_url=reg_url)


class register(tornado.web.UIModule):
    def render(self, form):
        login_url = '/login'
        try:
            next = form.next.data
            if next is not None:
                login_url += "?" + urllib.urlencode({'next':next})
        except AttributeError:
            pass
        return self.render_string('modules/register.html', form=form, login_url=login_url)


class filters(tornado.web.UIModule):
    def render(self, filters):
        return self.render_string("modules/filters.html", filters=filters)

    def embedded_javascript(self):
        return """
    $('.filters input[type="submit"]').hide();
    $('.filters form').bind('submit', function(e){
        e.preventDefault();

        var form = $(this);
        var url = form.attr('action');
        var params = form.serialize();

        $('#results').html("<blink>working...</blink>");
        $.ajax({
			type: "GET",
			url: url,
			data: params,
			success: function(data){
				$('#results').html(data);
                if(window.history.pushState) {
                    window.history.replaceState('', "FOOO!", url+"?"+params);
                }
			}
		});
    });
    $('.filters input').bind("change", function(e) {
        $('.filters form').submit();
    });
        """

class searchresults(tornado.web.UIModule):
    def render(self, pager):
        return self.render_string("modules/searchresults.html", pager=pager)

class paginator(tornado.web.UIModule):
    def render(self, pager):
        return self.render_string("modules/paginator.html", pager=pager)


class fmt_datetime(tornado.web.UIModule):
    def render(self, dt, cls=''):

        if cls:
            extra = 'class="%s"' % (cls,)
        else:
            extra = ''
        return '<time %sdatetime="%s">%s</time>' % (
            extra,
            dt.isoformat(),
            self.locale.format_date(dt, shorter=True)
            ) 

class fmt_date(tornado.web.UIModule):
    def render(self, d, cls=''):

        if cls:
            extra = 'class="%s"' % (cls,)
        else:
            extra = ''
        return '<time %sdatetime="%s">%s</time>' % (
            extra,
            d.isoformat(),
            d.strftime('%d %b %Y')
            ) 


class help_paper(tornado.web.UIModule):
    """ show help on tracking down academic papers """
    def render(self, art, journals, institutions, researchers):
        return self.render_string('modules/help_paper.html',
            art=art,
            institutions=institutions,
            journals=journals,
            researchers=researchers)


class help_pr(tornado.web.UIModule):
    """ show help on tracking down press releases """
    def render(self, art, journals, institutions, researchers):
        return self.render_string('modules/help_pr.html',
            art=art,
            institutions=institutions,
            journals=journals,
            researchers=researchers)


class help_other(tornado.web.UIModule):
    """ show help on tracking down other links """
    def render(self, art, journals, institutions, researchers):
        return self.render_string('modules/help_other.html',
            art=art,
            institutions=institutions,
            journals=journals,
            researchers=researchers)


