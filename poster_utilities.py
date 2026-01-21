#!/usr/bin/env python3

# MIT License

# Copyright (c) 2026 Rachid, Youven ZEGHLACHE
#!/usr/bin/env python3
"""
Inkscape Poster Utilities Extension
Adds title, authors, conference, and institution text to posters
Supports both Inkscape native text and LaTeX rendering
"""





import inkex
from inkex import TextElement, Transform, Tspan
import csv
import os
import tempfile
import subprocess
import shutil
from lxml import etree

POSTER_NS = "http://poster-utilities/namespace"

class PosterUtilities(inkex.EffectExtension):
    
    def add_arguments(self, pars):
        pars.add_argument("--tab", default="input")
        pars.add_argument("--backend", default="inkscape", help="Backend: inkscape or latex")
        
        # Direct input fields
        pars.add_argument("--title", default="", help="Title text")
        pars.add_argument("--authors", default="", help="Authors (semicolon separated)")
        pars.add_argument("--conference", default="", help="Conference name")
        pars.add_argument("--institution", default="", help="Institution (semicolon separated)")
        
        # Author-institution mapping
        pars.add_argument("--author_inst_map", default="", 
                         help="Author-institution mapping")
        pars.add_argument("--mapping_style", default="superscript", 
                         help="Style for institution markers")
        
        # CSV input
        pars.add_argument("--use_csv", type=inkex.Boolean, default=False)
        pars.add_argument("--csv_file", default="", help="Path to CSV file")
        
        # LaTeX options
        pars.add_argument("--latex_preamble", type=str, default="", help="LaTeX preamble")
        pars.add_argument("--latex_template", type=str, default="", help="Full LaTeX template")
        
        # Formatting
        pars.add_argument("--title_size", type=int, default=48)
        pars.add_argument("--author_size", type=int, default=32)
        pars.add_argument("--conf_size", type=int, default=28)
        pars.add_argument("--inst_size", type=int, default=24)
        pars.add_argument("--x_position", type=int, default=100)
        pars.add_argument("--y_position", type=int, default=100)
        pars.add_argument("--line_spacing", type=int, default=80)
        pars.add_argument("--text_align", default="left", help="Text alignment")

    def effect(self):
        # Get poster data
        if self.options.use_csv and self.options.csv_file:
            data = self.parse_csv(self.options.csv_file)
        else:
            data = {
                'title': self.options.title,
                'authors': self.options.authors,
                'conference': self.options.conference,
                'institution': self.options.institution,
                'author_inst_map': self.options.author_inst_map
            }
            #data = self.parse_csv(self.options.csv_file)

            
        # Debug output
        inkex.utils.debug(f"Data: {data}")
        inkex.utils.debug(f"Backend: {self.options.backend}")
        
        # Choose backend
        if self.options.backend == "latex":
            self.add_latex_elements(data)
        else:
            self.add_inkscape_elements(data)
    
    def parse_csv(self, csv_path):
        """Parse CSV file with poster data"""
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                row = next(reader)
                
                return {
                    'title': row.get('title', ''),
                    'authors': row.get('authors', ''),
                    'conference': row.get('conference', ''),
                    'institution': row.get('institutions', row.get('institution', '')),
                    'author_inst_map': row.get('author_inst_map', '')
                }
        except Exception as e:
            inkex.errormsg(f"Error reading CSV: {str(e)}")
            return {'title': '', 'authors': '', 'conference': '', 'institution': '', 'author_inst_map': ''}
    
    def parse_author_inst_mapping(self, authors_str, institutions_str, mapping_str):
        """Parse author-institution mapping"""
        authors = [a.strip() for a in authors_str.split(';') if a.strip()]
        institutions = [i.strip() for i in institutions_str.split(';') if i.strip()]
        
        if not mapping_str:
            # No mapping, return all authors and institutions separately
            return [(author, []) for author in authors], institutions
        
        author_mappings = []
        mappings = [m.strip() for m in mapping_str.split(';') if m.strip()]
        
        for i, mapping in enumerate(mappings):
            if ':' in mapping:
                # Explicit format: "Author Name:1,2"
                parts = mapping.split(':', 1)
                author_name = parts[0].strip()
                inst_indices = [int(idx.strip()) for idx in parts[1].split(',')]
                author_mappings.append((author_name, inst_indices))
            else:
                # Positional format: "1,2"
                if i < len(authors):
                    inst_indices = [int(idx.strip()) for idx in mapping.split(',')]
                    author_mappings.append((authors[i], inst_indices))
        
        return author_mappings, institutions
    
    def format_authors_with_institutions_inkscape(self, author_mappings, style='superscript'):
        """Format authors with institution markers for Inkscape
        Returns list of (author_text, marker_text, marker_style) tuples"""
        formatted_authors = []
        
        for author, inst_indices in author_mappings:
            if not inst_indices:
                formatted_authors.append((author, '', ''))
            else:
                if style == 'parenthesis':
                    markers = ','.join(str(i) for i in inst_indices)
                    formatted_authors.append((f"{author} ({markers})", '', ''))
                elif style == 'symbol':
                    symbols = ['*', '†', '‡', '§', '¶', '‖']
                    markers = ''.join(symbols[(i-1) % len(symbols)] for i in inst_indices)
                    formatted_authors.append((author, markers, 'normal'))
                elif style == 'superscript':
                    markers = ','.join(str(i) for i in inst_indices)
                    formatted_authors.append((author, markers, 'super'))
                elif style == 'subscript':
                    markers = ','.join(str(i) for i in inst_indices)
                    formatted_authors.append((author, markers, 'sub'))
                else:
                    formatted_authors.append((author, '', ''))
        
        return formatted_authors
    
    def format_institutions_with_numbers_inkscape(self, institutions, style='superscript'):
        """Format institutions with numbers for Inkscape"""
        formatted_insts = []
        
        for i, inst in enumerate(institutions, 1):
            if style == 'parenthesis':
                formatted_insts.append(f"({i}) {inst}")
            elif style == 'symbol':
                symbols = ['*', '†', '‡', '§', '¶', '‖']
                marker = symbols[(i-1) % len(symbols)]
                formatted_insts.append(f"{marker}{inst}")
            elif style == 'superscript':
                formatted_insts.append((str(i), inst, 'super'))
            elif style == 'subscript':
                formatted_insts.append((str(i), inst, 'sub'))
            else:
                formatted_insts.append(f"{i}. {inst}")
        
        return formatted_insts
    
    def wrap_text(self, text, max_chars=60):
        """Simple text wrapping by character count"""
        if not text:
            return ""
        
        words = text.split()
        lines = []
        current_line = []
        current_length = 0
        
        for word in words:
            word_length = len(word)
            if current_length + word_length + len(current_line) <= max_chars:
                current_line.append(word)
                current_length += word_length
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
                current_length = word_length
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return '\n'.join(lines)
    
    def add_inkscape_elements(self, data):
        """Add text using Inkscape native text elements"""
        group = inkex.Group()
        group.set('id', self.svg.get_unique_id('poster-group'))
        
        y_pos = self.options.y_position
        x_pos = self.options.x_position
        
        # Add Title
        if data.get('title'):
            title_text = self.wrap_text(data['title'], 50)
            title = self.create_text_element(
                title_text, x_pos, y_pos, 
                self.options.title_size, 'bold', self.options.text_align
            )
            group.append(title)
            y_pos += self.options.line_spacing
        
        # Add Authors with institution mapping
        if data.get('authors'):
            if data.get('author_inst_map') and data.get('institution'):
                author_mappings, institutions = self.parse_author_inst_mapping(
                    data['authors'], 
                    data['institution'], 
                    data['author_inst_map']
                )
                # Create authors with superscript/subscript markers
                authors_elem = self.create_authors_with_markers(
                    author_mappings, 
                    x_pos, y_pos,
                    self.options.author_size,
                    self.options.mapping_style,
                    self.options.text_align
                )
            else:
                authors_list = [a.strip() for a in data['authors'].split(';') if a.strip()]
                authors_text = ', '.join(authors_list)
                authors_wrapped = self.wrap_text(authors_text, 60)
                authors_elem = self.create_text_element(
                    authors_wrapped, x_pos, y_pos,
                    self.options.author_size, 'normal', self.options.text_align
                )
            
            group.append(authors_elem)
            y_pos += self.options.line_spacing
        
        # Add Conference
        if data.get('conference'):
            conf_text = self.wrap_text(data['conference'], 60)
            conference = self.create_text_element(
                conf_text, x_pos, y_pos,
                self.options.conf_size, 'italic', self.options.text_align
            )
            group.append(conference)
            y_pos += self.options.line_spacing
        
        # Add Institutions
        if data.get('institution'):
            if data.get('author_inst_map'):
                _, institutions = self.parse_author_inst_mapping(
                    data.get('authors', ''), 
                    data['institution'], 
                    data['author_inst_map']
                )
                # Create institutions with markers
                inst_elem = self.create_institutions_with_markers(
                    institutions,
                    x_pos, y_pos,
                    self.options.inst_size,
                    self.options.mapping_style,
                    self.options.text_align
                )
            else:
                inst_list = [i.strip() for i in data['institution'].split(';') if i.strip()]
                inst_text = ', '.join(inst_list)
                inst_wrapped = self.wrap_text(inst_text, 60)
                inst_elem = self.create_text_element(
                    inst_wrapped, x_pos, y_pos,
                    self.options.inst_size, 'normal', self.options.text_align
                )
            
            group.append(inst_elem)
        
        self.svg.get_current_layer().append(group)
    
    def create_text_element(self, text, x, y, font_size, font_weight, text_align='left'):
        """Create a text element with properties"""
        text_elem = TextElement()
        text_elem.text = text
        text_elem.set('x', str(x))
        text_elem.set('y', str(y))
        
        # Handle text alignment
        anchor = 'start'
        if text_align == 'center':
            anchor = 'middle'
        elif text_align == 'right':
            anchor = 'end'
        
        style = {
            'font-size': f'{font_size}px',
            'font-family': 'Arial, sans-serif',
            'font-weight': font_weight,
            'fill': '#000000',
            'text-anchor': anchor
        }
        text_elem.style = style
        
        return text_elem
    
    def create_authors_with_markers(self, author_mappings, x, y, font_size, style, text_align='left'):
        """Create text element with superscript/subscript markers for authors"""
        text_elem = TextElement()
        text_elem.set('x', str(x))
        text_elem.set('y', str(y))
        
        anchor = 'start'
        if text_align == 'center':
            anchor = 'middle'
        elif text_align == 'right':
            anchor = 'end'
        
        base_style = {
            'font-size': f'{font_size}px',
            'font-family': 'Arial, sans-serif',
            'font-weight': 'normal',
            'fill': '#000000',
            'text-anchor': anchor
        }
        text_elem.style = base_style
        
        formatted = self.format_authors_with_institutions_inkscape(author_mappings, style)
        
        for i, (author, marker, marker_style) in enumerate(formatted):
            if i > 0:
                # Add comma separator
                separator = Tspan()
                separator.text = ', '
                text_elem.append(separator)
            
            # Add author name
            author_tspan = Tspan()
            author_tspan.text = author
            text_elem.append(author_tspan)
            
            # Add marker if exists
            if marker:
                marker_tspan = Tspan()
                marker_tspan.text = marker
                
                if marker_style == 'super':
                    marker_tspan.style = {
                        'font-size': f'{int(font_size * 0.6)}px',
                        'baseline-shift': 'super'
                    }
                elif marker_style == 'sub':
                    marker_tspan.style = {
                        'font-size': f'{int(font_size * 0.6)}px',
                        'baseline-shift': 'sub'
                    }
                
                text_elem.append(marker_tspan)
        
        return text_elem
    
    def create_institutions_with_markers(self, institutions, x, y, font_size, style, text_align='left'):
        """Create text element with markers for institutions"""
        text_elem = TextElement()
        text_elem.set('x', str(x))
        text_elem.set('y', str(y))
        
        anchor = 'start'
        if text_align == 'center':
            anchor = 'middle'
        elif text_align == 'right':
            anchor = 'end'
        
        base_style = {
            'font-size': f'{font_size}px',
            'font-family': 'Arial, sans-serif',
            'font-weight': 'normal',
            'fill': '#000000',
            'text-anchor': anchor
        }
        text_elem.style = base_style
        
        formatted = self.format_institutions_with_numbers_inkscape(institutions, style)
        
        for i, item in enumerate(formatted):
            if i > 0:
                # Add comma separator
                separator = Tspan()
                separator.text = ', '
                text_elem.append(separator)
            
            if isinstance(item, tuple):
                # Superscript or subscript format
                number, inst, marker_style = item
                
                # Add number marker
                number_tspan = Tspan()
                number_tspan.text = number
                
                if marker_style == 'super':
                    number_tspan.style = {
                        'font-size': f'{int(font_size * 0.6)}px',
                        'baseline-shift': 'super'
                    }
                elif marker_style == 'sub':
                    number_tspan.style = {
                        'font-size': f'{int(font_size * 0.6)}px',
                        'baseline-shift': 'sub'
                    }
                
                text_elem.append(number_tspan)
                
                # Add institution name
                inst_tspan = Tspan()
                inst_tspan.text = inst
                text_elem.append(inst_tspan)
            else:
                # Simple string format
                inst_tspan = Tspan()
                inst_tspan.text = item
                text_elem.append(inst_tspan)
        
        return text_elem
    
    def add_latex_elements(self, data):
        """Add text using LaTeX rendered to SVG"""
        
        # Build LaTeX content
        if self.options.latex_template:
            latex_content = self.apply_template(self.options.latex_template, data)
        else:
            latex_content = self.build_default_latex(data)
        
        # Debug: show generated LaTeX
        inkex.utils.debug("Generated LaTeX:")
        inkex.utils.debug(latex_content[:500])
        
        # Render LaTeX to SVG
        try:
            svg_file = self.render_latex_to_svg(latex_content)
            self.import_latex_svg(svg_file)
        except Exception as e:
            inkex.errormsg(f"LaTeX rendering failed: {str(e)}")
            inkex.utils.debug(f"LaTeX error details: {str(e)}")
            # Fallback to Inkscape backend
            inkex.utils.debug("Falling back to Inkscape backend")
            self.add_inkscape_elements(data)
    
    def apply_template(self, template, data):
        """Apply data to user template"""
        result = template
        for key, value in data.items():
            placeholder = '{' + key + '}'
            result = result.replace(placeholder, str(value) if value else '')
        return result
    
    def build_default_latex(self, data):
        """Build default LaTeX document"""
        
        # Get preamble from options or use default
        preamble_packages = self.options.latex_preamble if self.options.latex_preamble else r"""\usepackage[utf8]{inputenc}
\usepackage{amsmath}
\usepackage{amsfonts}"""
        
        # Title
        title_tex = r"\textbf{\Huge %s}" % self.escape_latex(data.get('title', '')) if data.get('title') else ""
        
        # Authors with institution mapping
        authors_tex = ""
        inst_tex = ""
        
        if data.get('authors'):
            if data.get('author_inst_map') and data.get('institution'):
                author_mappings, institutions = self.parse_author_inst_mapping(
                    data['authors'], 
                    data['institution'], 
                    data['author_inst_map']
                )
                
                # Format authors with superscripts
                formatted_authors = []
                for author, inst_indices in author_mappings:
                    if inst_indices:
                        superscripts = ','.join(str(i) for i in inst_indices)
                        formatted_authors.append(f"{self.escape_latex(author)}$^{{{superscripts}}}$")
                    else:
                        formatted_authors.append(self.escape_latex(author))
                
                authors_tex = r"\Large " + ', '.join(formatted_authors)
                
                # Format institutions with numbers
                inst_lines = []
                for i, inst in enumerate(institutions, 1):
                    inst_lines.append(f"$^{{{i}}}${self.escape_latex(inst)}")
                inst_tex = r"\normalsize " + r", ".join(inst_lines)
            else:
                authors_list = [a.strip() for a in data['authors'].split(';')]
                authors_tex = r"\Large " + ", ".join([self.escape_latex(a) for a in authors_list])
                
                # Simple institutions
                if data.get('institution'):
                    inst_list = [i.strip() for i in data['institution'].split(';')]
                    inst_tex = r"\normalsize " + ", ".join([self.escape_latex(i) for i in inst_list])
        
        # Conference
        conf_tex = r"\textit{\large %s}" % self.escape_latex(data.get('conference', '')) if data.get('conference') else ""
        
        # Build document
        content_parts = [p for p in [title_tex, authors_tex, conf_tex, inst_tex] if p]
        content = "\n\n\\vspace{0.3cm}\n\n".join(content_parts)
        
        document = r"""\documentclass{article}
%s
\pagestyle{empty}
\begin{document}
\begin{flushleft}
%s
\end{flushleft}
\end{document}
""" % (preamble_packages, content)
        
        return document
    
    def escape_latex(self, text):
        """Escape special LaTeX characters"""
        if not text:
            return ""
        replacements = {
            '\\': r'\textbackslash{}',
            '&': r'\&',
            '%': r'\%',
            '$': r'\$',
            '#': r'\#',
            '_': r'\_',
            '{': r'\{',
            '}': r'\}',
            '~': r'\textasciitilde{}',
            '^': r'\textasciicircum{}'
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text
    
    def render_latex_to_svg(self, latex_content):
        """Compile LaTeX to PDF then convert to SVG"""
        # Create a persistent temp directory that won't be deleted
        tmpdir = tempfile.mkdtemp(prefix='inkscape_latex_')
        
        try:
            tex_file = os.path.join(tmpdir, 'poster.tex')
            pdf_file = os.path.join(tmpdir, 'poster.pdf')
            svg_file = os.path.join(tmpdir, 'poster.svg')
            
            # Write LaTeX file
            with open(tex_file, 'w', encoding='utf-8') as f:
                f.write(latex_content)
            
            inkex.utils.debug(f"LaTeX file written to: {tex_file}")
            
            # Compile LaTeX to PDF
            result = subprocess.run(
                ['pdflatex', '-interaction=nonstopmode', '-halt-on-error', 
                 '-output-directory', tmpdir, tex_file],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=tmpdir
            )
            
            if result.returncode != 0 or not os.path.exists(pdf_file):
                error_msg = f"LaTeX compilation failed:\nSTDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
                raise Exception(error_msg)
            
            inkex.utils.debug(f"PDF created: {pdf_file}")
            
            # Convert PDF to SVG using Inkscape command line
            # Try multiple methods
            svg_created = False
            
            # Method 1: Using inkex.command.inkscape
            try:
                inkex.command.inkscape(
                    pdf_file,
                    export_filename=svg_file,
                    pdf_poppler=True,
                    export_type='svg',
                    export_text_to_path=True,
                    export_area_drawing=True
                )
                if os.path.exists(svg_file):
                    svg_created = True
                    inkex.utils.debug("Method 1 (inkex.command) succeeded")
            except Exception as e:
                inkex.utils.debug(f"Method 1 failed: {e}")
            
            # Method 2: Direct subprocess call
            if not svg_created:
                try:
                    result = subprocess.run(
                        ['inkscape', pdf_file, '--export-filename=' + svg_file,
                         '--pdf-poppler', '--export-type=svg', '--export-text-to-path',
                         '--export-area-drawing'],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    if os.path.exists(svg_file):
                        svg_created = True
                        inkex.utils.debug("Method 2 (subprocess) succeeded")
                except Exception as e:
                    inkex.utils.debug(f"Method 2 failed: {e}")
            
            # Method 3: Simple conversion without extra options
            if not svg_created:
                try:
                    result = subprocess.run(
                        ['inkscape', pdf_file, '--export-filename=' + svg_file],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    if os.path.exists(svg_file):
                        svg_created = True
                        inkex.utils.debug("Method 3 (simple) succeeded")
                except Exception as e:
                    inkex.utils.debug(f"Method 3 failed: {e}")
            
            if not svg_created:
                raise Exception(f"PDF to SVG conversion failed. PDF exists at: {pdf_file}")
            
            inkex.utils.debug(f"SVG created: {svg_file}")
            
            # Copy SVG to a new location to avoid temp directory issues
            final_svg = os.path.join(tmpdir, 'poster_final.svg')
            shutil.copy2(svg_file, final_svg)
            
            return final_svg
            
        except Exception as e:
            # Don't delete temp directory on error for debugging
            inkex.utils.debug(f"Temp directory preserved at: {tmpdir}")
            raise e
    
    def import_latex_svg(self, svg_file):
        """Import rendered LaTeX SVG into document"""
        try:
            # Parse the SVG file
            tree = etree.parse(svg_file)
            root = tree.getroot()
            
            # Create a group for the imported content
            group = inkex.Group()
            group.set('id', self.svg.get_unique_id('poster-latex-group'))
            
            # Import all elements from the SVG
            svg_ns = {'svg': 'http://www.w3.org/2000/svg'}
            for element in root:
                # Skip metadata and defs for now, copy visual elements
                tag = etree.QName(element.tag).localname
                if tag not in ['metadata', 'defs']:
                    group.append(element)
            
            # Also import defs if they exist
            defs = root.find('.//svg:defs', svg_ns)
            if defs is not None:
                # Add defs to document defs
                doc_defs = self.svg.defs
                for def_element in defs:
                    doc_defs.append(def_element)
            
            # Position the group
            transform = Transform()
            transform.add_translate(self.options.x_position, self.options.y_position)
            group.transform = transform
            
            # Add to current layer
            self.svg.get_current_layer().append(group)
            
            inkex.utils.debug("SVG imported successfully")
            
        except Exception as e:
            inkex.errormsg(f"Error importing SVG: {str(e)}")
            raise


if __name__ == '__main__':
    PosterUtilities().run()