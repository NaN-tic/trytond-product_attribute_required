# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.transaction import Transaction

__metaclass__ = PoolMeta
__all__ = ['Template', 'Product']


class Template:
    __name__ = 'product.template'

    @classmethod
    def __setup__(cls):
        super(Template, cls).__setup__()
        cls.products.context.update({
                'template_attribute_set': Eval('attribute_set'),
                })

    @fields.depends('attribute_set', 'products')
    def on_change_attribute_set(self):
        products = []
        for product in self.products:
            if product.attribute_set != self.attribute_set:
                changes = {
                        'id': product.id,
                        'attribute_set': (self.attribute_set.id
                            if self.attribute_set else None),
                        }
                product.attribute_set = self.attribute_set
                changes.update(product.on_change_attribute_set())
                products.append(changes)
        if products:
            return {'products': {'update': products}}
        return {}


class Product:
    __name__ = 'product.product'

    @classmethod
    def __setup__(cls):
        super(Product, cls).__setup__()
        cls.attributes.context.update({
                'attribute_set': Eval('attribute_set'),
                })
        cls._error_messages.update({
                'required_attribute': ('The field attributes is requried on '
                    'product %s.'),
                })

    @classmethod
    def default_attributes(cls):
        pool = Pool()
        AttributeSet = pool.get('product.attribute.set')
        context = Transaction().context
        set_id = context.get('attribute_set',
            context.get('template_attribute_set'))
        if set_id:
            return cls.compute_attribute_values(AttributeSet(set_id))

    @staticmethod
    def compute_attribute_values(attribute_set):
        attributes = {}
        for attribute in attribute_set.attributes:
            attributes[attribute.name] = None
        return attributes

    @fields.depends('attribute_set', 'template',
        '_parent_template.attribute_set')
    def on_change_template(self):
        try:
            changes = super(Product, self).on_change_template()
        except AttributeError:
            changes = {}
        self.attribute_set = self.on_change_with_attribute_set()
        changes.update(self.on_change_attribute_set())
        return changes

    @fields.depends('attribute_set', 'template',
        '_parent_template.attribute_set')
    def on_change_attribute_set(self):
        try:
            changes = super(Product, self).on_change_attribute_set()
        except AttributeError:
            changes = {}

        changes.update({'attributes': {}})
        if not self.attribute_set:
            return changes
        return {
            'attributes': self.compute_attribute_values(self.attribute_set),
            }

    @classmethod
    def validate(cls, records):
        for record in records:
            record.check_required_attributes()

    def check_required_attributes(self):
        if not self.attribute_set:
            return
        for name, value in self.attributes.iteritems():
            if value is None:
                self.raise_user_error('required_attribute', self.rec_name)
        keys = set([x.name for x in self.attribute_set.attributes])
        if set(self.attributes) < keys:
            self.raise_user_error('required_attribute', self.rec_name)
