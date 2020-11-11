import sqlalchemy as sa


__all__ = ['metadata', 'owners_table', 'questions_table', 'search_types_table']


metadata = sa.MetaData()

search_types_table = sa.Table(
    'search_types',
    metadata,
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('intitle', sa.Text),
    sa.Column('sort', sa.Text),
    sa.Column('order', sa.Text),
    sa.UniqueConstraint('intitle', 'sort', 'order'),
)

owners_table = sa.Table(
    'owners',
    metadata,
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('user_id', sa.Integer),
    sa.Column('reputation', sa.Integer),
    sa.Column('user_type', sa.Text),
    sa.Column('accept_rate', sa.Text),
    sa.Column('profile_image', sa.Text),
    sa.Column('display_name', sa.Text),
    sa.Column('link', sa.Text),
)

questions_table = sa.Table(
    'questions',
    metadata,
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('is_answered', sa.Boolean, nullable=False),
    sa.Column('accepted_answer_id', sa.Integer),
    sa.Column('view_count', sa.Integer),
    sa.Column('bounty_amount', sa.DateTime),
    sa.Column('bounty_closes_date', sa.Integer),
    sa.Column('answer_count', sa.Integer, nullable=False),
    sa.Column('score', sa.Integer, nullable=False),
    sa.Column('last_activity_date', sa.DateTime, nullable=False),
    sa.Column('creation_date', sa.DateTime, nullable=False),
    sa.Column('last_edit_date', sa.DateTime),
    sa.Column('closed_date', sa.DateTime),
    sa.Column('locked_date', sa.DateTime),
    sa.Column('protected_date', sa.DateTime),
    sa.Column('community_owned_date', sa.DateTime),
    sa.Column('closed_reason', sa.Text),
    sa.Column('question_id', sa.Integer, nullable=False),
    sa.Column('content_license', sa.Text),
    sa.Column('link', sa.Text, nullable=False),
    sa.Column('title', sa.Text, nullable=False),
    sa.Column('tags', sa.ARRAY(sa.Text), nullable=False),
    sa.Column(
        'search_type_id',
        sa.Integer,
        sa.ForeignKey('search_types.id', ondelete="cascade"),
        nullable=False,
    ),
    sa.Column(
        'owner_id',
        sa.Integer,
        sa.ForeignKey('owners.id', ondelete="cascade"),
        nullable=False,
    ),
    sa.Column(
        'creation_at', sa.DateTime, nullable=False, server_default=sa.func.now()
    ),
)
