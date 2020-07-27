from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterFeatureSink
from qgis.core import QgsProcessingParameterNumber
import processing


class Wmeasure(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterVectorLayer('camadadeentrada', 'Camada de Entrada', types=[QgsProcessing.TypeVector], defaultValue=None))
        self.addParameter(QgsProcessingParameterFeatureSink('Resultado', 'RESULTADO', optional=True, type=QgsProcessing.TypeVectorAnyGeometry, createByDefault=True, defaultValue=None))
        self.addParameter(QgsProcessingParameterNumber('raiodetolerncia', 'Raio de Tolerancia', type=QgsProcessingParameterNumber.Integer, minValue=0, maxValue=9999, defaultValue=1))
        self.addParameter(QgsProcessingParameterVectorLayer('camadadereferncia', 'Camada de Referencia', types=[QgsProcessing.TypeVectorLine], defaultValue=None))
        self.addParameter(QgsProcessingParameterNumber('valordesplit', 'Cadência de Segmentacao', type=QgsProcessingParameterNumber.Integer, minValue=0, maxValue=9999, defaultValue=1))

    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        feedback = QgsProcessingMultiStepFeedback(7, model_feedback)
        results = {}
        outputs = {}

        # Quebra de linha por comprimento maximo
        alg_params = {
            'INPUT': parameters['camadadereferncia'],
            'LENGTH': parameters['valordesplit'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['QuebraDeLinhaPorComprimentoMaximo'] = processing.run('native:splitlinesbylength', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(1)
        if feedback.isCanceled():
            return {}

        # Adicionar campo de autoincremento
        alg_params = {
            'FIELD_NAME': 'IDS',
            'GROUP_FIELDS': None,
            'INPUT': outputs['QuebraDeLinhaPorComprimentoMaximo']['OUTPUT'],
            'SORT_ASCENDING': True,
            'SORT_EXPRESSION': '',
            'SORT_NULLS_FIRST': False,
            'START': 1,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['AdicionarCampoDeAutoincremento'] = processing.run('native:addautoincrementalfield', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(2)
        if feedback.isCanceled():
            return {}

        # Extrair vertices
        alg_params = {
            'INPUT': outputs['AdicionarCampoDeAutoincremento']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ExtrairVertices'] = processing.run('native:extractvertices', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(3)
        if feedback.isCanceled():
            return {}

        # Extrair por atributo
        alg_params = {
            'FIELD': 'vertex_index',
            'INPUT': outputs['ExtrairVertices']['OUTPUT'],
            'OPERATOR': 0,
            'VALUE': '1',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ExtrairPorAtributo'] = processing.run('native:extractbyattribute', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(4)
        if feedback.isCanceled():
            return {}

        # Ajustar geometrias a camada
        alg_params = {
            'BEHAVIOR': 3,
            'INPUT': parameters['camadadeentrada'],
            'REFERENCE_LAYER': outputs['ExtrairPorAtributo']['OUTPUT'],
            'TOLERANCE': parameters['raiodetolerncia'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['AjustarGeometriasACamada'] = processing.run('qgis:snapgeometries', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(5)
        if feedback.isCanceled():
            return {}

        # Calculadora de campo
        alg_params = {
            'FIELD_LENGTH': 9999,
            'FIELD_NAME': 'DISTÂNCIA',
            'FIELD_PRECISION': 1,
            'FIELD_TYPE': 1,
            'FORMULA': '\"distance\"*\"IDS\"',
            'INPUT': outputs['ExtrairPorAtributo']['OUTPUT'],
            'NEW_FIELD': True,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['CalculadoraDeCampo'] = processing.run('qgis:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(6)
        if feedback.isCanceled():
            return {}

        # Unir atributos pela posicao
        alg_params = {
            'DISCARD_NONMATCHING': False,
            'INPUT': outputs['AjustarGeometriasACamada']['OUTPUT'],
            'JOIN': outputs['CalculadoraDeCampo']['OUTPUT'],
            'JOIN_FIELDS': 'DISTÂNCIA',
            'METHOD': 0,
            'PREDICATE': [0,1,3,4,5,6],
            'PREFIX': '',
            'OUTPUT': parameters['Resultado']
        }
        outputs['UnirAtributosPelaPosicao'] = processing.run('qgis:joinattributesbylocation', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Resultado'] = outputs['UnirAtributosPelaPosicao']['OUTPUT']
        return results

    def name(self):
        return 'wMeasure'

    def displayName(self):
        return 'wMeasure'

    def group(self):
        return 'Vetores'

    def groupId(self):
        return 'Vetores'

    def createInstance(self):
        return Wmeasure()
