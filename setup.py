from setuptools import setup

setup(
    name='CompetenceDB',
    version='1.3.0',
    packages=['app','app.mod_admin','app.mod_competence','app.mod_document','app.mod_training', 'app.mod_hos', 'app.mod_cpd'],
    url='',
    license='',
    zip_safe=False,
    author='Matthew Parker',
    author_email='matthew.parker@sheffield.ac.uk',
    description='Competence Management Application',
    include_package_data=True
)
