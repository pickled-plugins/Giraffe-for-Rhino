"""
Giraffe for Rhino v1.0.0 Beta
Peter Szerzo
"""

import math
import string
import rhinoscriptsyntax as rs
import rhinoinput as ri


plural_to_sofi = {

    "nodes": "node", 
    "beams": "beam", 
    "trusses": "trus", 
    "cables": "cabl", 
    "springs": "spri",
    "quads": "quad"

}

line_elements = [ "beams", "trusses", "cables" ]


tolerance = 0.1 # how close points have to be to be considered one


class GiraffeLayer():
    

    @classmethod
    def get_all(self):

        """Returns a list of all layers as GiraffeLayer objects."""

        layer_names = rs.LayerNames()

        layers = []

        for layer_name in layer_names:
        
            layers.append(GiraffeLayer(layer_name))

        return layers


    def __init__(self, name):

        """Constructor.
        Parameters:
          name = object name
        """
        
        self.name = name
        self.path = name.split("::")
        self.depth = len(self.path)
        self.last = self.path[self.depth - 1]
        
        return self


    def create(self):
    
        """Creates layer within Rhino, including all ancestors.
        Returns:
          self
        """

        mom = ""
        
        for s in self.path:
            
            son = s if (mom == "") else (mom + "::" + s)

            mommy = None if mom == "" else mom

            if(not rs.IsLayer(son)):

                rs.AddLayer(s, color = None, visible = True, locked = False, parent = mommy)

            mom = son
            
        return self


    def get_geometry(self):

        """Returns geometry from a given layer as a list. Sublayer objects are not included."""

        return rs.ObjectsByLayer(self.name)


    def clear(self):

        """Deletes all objects from a given layer. Sublayer objects are kept.
        Returns:
          self
        """
    
        objects = self.get_geometry()

        for obj in objects:

            rs.DeleteObject(obj) 
            
        return self


    def get_grp(self):

        """Returns group number from layer."""

        grp = -1

        if (self.depth > 2):

            inp = ri.RhinoInput(self.path[2])

            grp = inp.get_no()

        return grp


    def get_name(self):

        """Returns group name from layer (last child only)."""

        return ri.RhinoInput(self.last).get_name()


    def get_prop(self):

        """Returns structural properties from layer (last child only)."""

        if (self.depth == 2):

            return ""

        return ri.RhinoInput(self.last).get_prop()


    def get_type(self):

        """Returns element type."""

        return plural_to_sofi[self.path[1]]


    def export(self):

        """Returns SOFiSTiK export."""

        name = self.get_name()
        grp = self.get_grp()
        typ = self.get_type()
        prop = self.get_prop()

        grp_string = ""

        if (grp != -1):

            grp_string = "grp " + str(grp)

        output = "\n\n!*!Label " + self.path[1] + " .. " + grp_string + " .. " + self.get_name() + "\n"

        if (grp_string != ""):

            output += grp_string + "\n"

        if (prop != ""):

            output += typ + " prop " + prop + "\n"

        return output


class StructuralElement:


    def __init__(self, geo, typ, grp = -1):

        """Constructor.
        Parameters:
          geo = Guid from Rhino; None if it does not exist (e.g. line endpoints)
          typ = object type
          grp = group number
        """
        
        self.geo = geo
        self.typ = typ

        self.grp = grp

        # default values
        self.no = -1
        self.prop = ""
        self.name = ""
        self.strict_naming = False

        # reference to containing layer
        self.layer = None

        self.build_base()


    def build_base(self):

        """Sets element attributes based on Guid name from Rhino."""

        # start- and endpoints of lines are nodes, but they do not need to have a point object associated to them
        # in this case, self.geo is None and the no, prop and name attributes stay as the default values set in the constructor
        if (self.geo):

            attr = ri.RhinoInput(rs.ObjectName(self.geo))

            self.no = attr.get_no()
            if (self.no != -1):
                self.strict_naming = True

            self.name = attr.get_name()
            self.prop = attr.get_prop()
        

    def export_base(self):

        """SOFiSTiK export common to all elements."""
    
        return (self.typ + " no " + str(self.no))



class Node(StructuralElement):
    

    def __init__(self, obj, coordinates = None):

        """Constructor.
        Parameters:
          obj = Guid from Rhino
          coordinates = if there is no Guid, coordinates should be set
        """
        
        StructuralElement.__init__(self, obj, "node")
        self.build(coordinates)
        
        
    def build(self, coordinates = None):

        """Build node from Rhino Guid or coordinates, whichever is set.
        Parameters:
          coordinates = coordinate array passed from constructor
        """

        # start- and endpoints of lines are nodes, but they do not need to have a point object associated to them
        # in this case, point coordinates should be set
        if (self.geo):
            coordinates = rs.PointCoordinates(self.geo)

        self.x = round(+ coordinates[0], 5)
        self.y = round(+ coordinates[1], 5)
        self.z = round(+ coordinates[2], 5)
        

    def distance_to(self, n):
        
        """Returns distance to specified node.
        Parameters:
          n = node to which distance is evaluated
        Returns:
          distance to n
        """

        d = ( (self.x - n.x) ** 2 + (self.y - n.y) ** 2 + (self.z - n.z) ** 2 ) ** 0.5
        
        return d
        
        
    def identical_to(self, n):

        """Returns True if node overlaps with specified node (distance smaller than tolerance)."""
        
        return (self.distance_to(n) < tolerance)


    def export_coordinates(self):

        """Returns coordinate export."""

        return "x " + str(self.x) + "*#conversion_factor" + " y " + str(self.y) + "*#conversion_factor" + " z " + str(self.z) + "*#conversion_factor"


    def export(self):
        
        """Returns SOFiSTiK export."""

        output = self.export_base() + " " + self.export_coordinates() + " " + self.prop

        if (self.name != ""):
            output += "$ " + self.name

        return output



class LineElement(StructuralElement):


    def __init__(self, obj, typ):

        """Constructor."""

        StructuralElement.__init__(self, obj, typ)
        self.n1 = None
        self.n2 = None


    def build(self):

        """Placeholder for a method analogous to Node.build()."""

        return True


    def identical_to(self, elem):

        """Returns true for overlapping line elements (identical start- and endnodes)."""

        return (self.n1 == elem.n1) and (self.n2 == elem.n2)


    def export(self):

        """Returns SOFiSTiK export."""

        output = self.export_base() + " na " + str(self.n1.no) + " ne " + str(self.n2.no) + " " + self.prop

        if (self.name != ""):
            output += "$ " + self.name

        return output



class ElementList:


    def __init__(self, name):

        """Constructor."""
        
        self.name = name
        self._list = []
        self._errors = []
        

    def get_identical_to(self, element):

        """Returns first element in the list that is identical to the specified element. Returns None if none found."""

        already_in_list = False
        
        for item in self._list:

            if element.identical_to(item):

                return item

        return None


    def is_taken_number(self, number, grp = -1):
        
        """Returns True if a number if taken in a given group.
        Parameters:
          number = element number
          grp = group number
        Returns:
          whether the given number/group combination is already taken
        """

        for element in self._list:
            
            if (element.no == number and element.grp == grp):
                
                return True
                
        return False


    def get_available_number(self, grp = -1):
    
        """Returns lowest available number for a given group in the list.
        Parameters:
          grp = group number
        """

        number = 1

        while(self.is_taken_number(number, grp)):
            
            number += 1

        return number    


    def get_conflicting_element(self, new_element):

        """Returns element with a numbering conflict.
        Parameters:
          new_element
        Returns:
          conflicting element
        """

        for element in self._list:
            
            if (element.no == new_element.no and element.grp == new_element.grp):
                
                return element
                
        return None


    def add_number(self, element):

        """Add first available number to any element."""

        element.no = self.get_available_number(element.grp)

 
    def resolve_numbering_conflict(self, existing_element, new_element):

        """Resolves numbering conflict between two elements based on specified rules.
        Parameters:
          existing_element = element already in list
          new_element = element to be inserted into the list
        Returns:
          self
        """

        # rule 1: if the element already in the list does not have strict naming, the new element keeps its number
        if (not existing_element.strict_naming):

            self.add_number(existing_element)

        # rule 2: if both conflicting elements have strict naming, the old element keeps its number; warning thrown
        else:

            self.add_number(new_element)

            self._errors.append("Numbering conflict, node number " + str(existing_element.no) + " changed to " + str(new_element.no) + ".")

        return self


    def add(self, new_element):

        """
        Adds new element to the list.
        If identical element is found in the list, the method returns that element and does not add the new one.
        If the new element has a -1 number (not specified), a new number is assigned.
        If the new element has a number, potential numbering conflicts are resolved.
        """
        
        identical = self.get_identical_to(new_element)

        if(identical):

            return identical

        else:

            if(new_element.no == -1):

                self.add_number(new_element)

            else:

                conflict = self.get_conflicting_element(new_element)

                if (conflict):

                    self.resolve_numbering_conflict(conflict, new_element)
            
            self._list.append(new_element)

            return new_element


    def export(self):

        """Returns SOFiSTiK export."""

        output = ""

        for item in self._errors:
            
            output += "$ " + item + "\n"

        current_layer = -1

        for item in self._list:
            
            previous_layer = current_layer

            current_layer = item.layer

            if (current_layer and (not previous_layer == current_layer)):

                output += current_layer.export()

            output += item.export() + "\n"
            
        output += "\n"

        return output



class StructuralModel:
    

    unit_conversion = {
        2: 0.001,
        3: 0.01,
        4: 1.0,
        8: 0.0254,
        9: 0.3048
    }
    

    """Constructor
    Parameters:
      name = model name
    """

    def __init__(self, name):   
    
        self.setup()

        self.name = name    
        
        self.nodes = ElementList("Nodes")
        self.beams = ElementList("Beams")
                
        self.gdiv = 1000
        self.current_group = -1
        
        self.output_header = "$ generated by Giraffe for Rhino\n"
        self.output_header += "+prog sofimsha\nhead " + self.name + "\n\nsyst init gdiv 1000\n"

        self.output_header += "\nlet#conversion_factor " + str(self.conversion_factor)

        self.output_footer = "\nend"

        return self


    def setup(self):

        """Sets up structural model."""

        self.conversion_factor = StructuralModel.unit_conversion[rs.UnitSystem()]

        return self


    def add_objects_from_layer(self, layer):

        """Adds objects from a given layer to the ElementLists of the structural model."""

        if (layer.depth > 1 and layer.path[0] == "input"):

            objects = layer.get_geometry()

            typ_plural = layer.path[1]
            typ_sofi = plural_to_sofi[typ_plural]

            if (typ_plural == "nodes"):

                for obj in objects:

                    if (rs.ObjectType(obj) == 1):

                        n = Node(obj)
                        n.layer = layer

                        self.nodes.add(n)

            if (typ_plural in line_elements):

                for obj in objects:

                    if (rs.ObjectType(obj) == 4):

                        bm = LineElement(obj, typ_sofi)

                        bm.layer = layer

                        # adds beam endpoints to node list, if not already existing
                        # if the node was already defined, self.nodes.add() will return that node
                        bm.n1 = self.nodes.add(Node(None, rs.CurveStartPoint(obj)))
                        bm.n2 = self.nodes.add(Node(None, rs.CurveEndPoint(obj)))

                        self.beams.add(bm)

        return self


    def export(self):

        """Returns SOFiSTiK export."""
        
        return self.output_header + self.nodes.export() + self.beams.export() + self.output_footer


    def make_file(self):

        """Creates or updates exported file.
        Returns:
          self
        """

        path = rs.DocumentPath()

        i = path.rfind("\\")

        path = path[:i-3]
        
        f = open(path + ".dat", "w")
        
        f.write(self.export())
        
        f.close()

        return self



def Main():
    
    sofi = StructuralModel("structure")

    layers = GiraffeLayer.get_all()
                    
    for layer in layers:

        sofi.add_objects_from_layer(layer)
                    
    sofi.make_file()
    
Main()