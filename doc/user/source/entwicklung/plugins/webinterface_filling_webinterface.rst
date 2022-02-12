.. index:: Web Interface

.. role:: redsup
.. role:: bluesup


Das Webinterface mit Inhalt füllen
----------------------------------

Die folgenden Schritte dienen dazu, das Webinterface mit Leben zu füllen:

   1. Die Methode ``index`` der Klasse ``WebInterface`` wird zur Übergabe der gewünschten Daten an das Template modifiziert (im folgenden Beispiel ist das eine Liste von Items, die das Attribut ``knx_dpt`` besitzen).

      Der Beispielcode wird wie folgt verändert von:

      .. code-block:: PYTHON

         @cherrypy.expose
         def index(self, reload=None):
             """
             Build index.html for cherrypy

             Render the template and return the html file to be delivered to the browser

             :return: contents of the template after beeing rendered
             """
             # add values to be passed to the Jinja2 template eg: tmpl.render(p=self.plugin, interface=interface, ...)
             tmpl = self.tplenv.get_template('index.html')
             return tmpl.render(p=self.plugin)

      zu:

      .. code-block:: PYTHON

              @cherrypy.expose
              def index(self, reload=None):
                  """
                  Build index.html for cherrypy

                  Render the template and return the html file to be delivered to the browser

                  :return: contents of the template after beeing rendered
                  """
                  tmpl = self.tplenv.get_template('index.html')
                  # add values to be passed to the Jinja2 template eg: tmpl.render(p=self.plugin, interface=interface, ...)
                  return tmpl.render(p=self.plugin)

                  # get list of items with the attribute knx_dpt
                  plgitems = []
                  for item in self.items.return_items():
                      if 'knx_dpt' in item.conf:
                          plgitems.append(item)

                  # additionally hand over the list of items, sorted by item-path
                  tmpl = self.tplenv.get_template('index.html')
                  return tmpl.render(p=self.plugin,
                                     items=sorted(plgitems, key=lambda k: str.lower(k['_path'])),
                                    )

   2. Das Template ``webif/templates/index.html`` wird zur Anzeige der gewünschten Daten angepasst.
      Um im ersten Tab des Webinterface die Items anzuzeigen, die der obige Beispielcode zusammengestellt hat, wird der folgende Code zwischen ``{% block bodytab1 %}`` und ``{% endblock bodytab1 %}`` eingefügt. Es ist sicherzustellen, dass korrekter HTML Code
      für die Tabellen genutzt wird, ua. durch Nutzen der Tags ``<thead>`` und ``<tbody>``
      sowie der jeweiligen End-Tags. Außerdem muss jeder Tabelle eine einzigartige ID vergeben werden.

      .. code-block:: HTML

         <div class="table-responsive" style="margin-left: 3px; margin-right: 3px;" class="row">
             <div class="col-sm-12">
                 <table id="maintable" class="table table-striped table-hover pluginList">
                     <thead>
                         <tr>
                             <th>{{ _('Item') }}</th>
                             <th>{{ _('Typ') }}</th>
                             <th>{{ _('knx_dpt') }}</th>
                         </tr>
                     </thead>
                     <tbody>
                         {% for item in items %}
                             <tr>
                                 <td class="py-1">{{ item._path }}</td>
                                 <td class="py-1">{{ item._type }}</td>
                                 <td class="py-1">{{ item.conf['knx_dpt'] }}</td>
                             </tr>
                         {% endfor %}
                     </tbody>
                 </table>
             </div>
         </div>

   3. Folgender Scriptcode muss zwischen ``{% block pluginscripts %}`` und
      ``{% endblock pluginscripts %}`` eingefügt werden, um ein Filtern und Sortieren
      der Tabellen zu ermöglichen.
      Der Code ``$('#maintable').DataTable( {} );``
      muss für jede Tabelle, für die Filtern/Sortieren ermöglicht werden soll, kopiert werden.
      Dabei ist sicher zu stellen, dass die ID (#maintable) jeweils richtig angepasst wird.
      Den entsprechenden ``<table>`` Tags sind die entsprechenden ids zu vergeben, außerdem sollte die
      CSS Klasse ``display`` hinzugefügt werden.
      Beispiel: ``<table id="maintable" class="table table-striped table-hover pluginList display">``.

      .. code-block:: HTML

          <script>
            $(document).ready( function () {
        			$(window).trigger('datatables_defaults'); // loading default behaviour
        			try {
      					$('#maintable').DataTable( {} ); // put options into {} if needed
      					$('#<table_id>').DataTable( {} ); // delete or change name
      				}
        			catch (e) {
      					console.log("Datatable JS not loaded, showing standard table without reorder option " + e)
      				}
            });
          </script>

   4. Das Logo oben links auf der Seite wird automatisch durch das Logo des konfigurierten Plugin-Typs ersetzt. Wenn das Webinterface ein eigenes Logo mitbringen soll, muss das entsprechende Bild im Verzeichnis ``webif/static/img`` mit dem Namen ``plugin_logo`` abgelegt sein. Die zulässigen Dateiformate sind **.png**, **.jpg** oder **.svg**. Dabei sollte die Größe der Bilddatei die Größe des angezeigten Logos (derzeit ca. 180x150 Pixel) nicht überschreiten, um unnötige Datenübertragungen zu vermeiden.
