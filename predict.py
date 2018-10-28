from keras.models import load_model
import os
import config as cf
def create_keras_model():
    """
    This function compiles and returns a Keras model.
    Should be passed to KerasClassifier in the Keras scikit-learn API.
    """

    # model = Sequential()
    # model.add(BatchNormalization(momentum=0.8, input_shape=(cf.ROW_LENGTH, 4),axis=1))
    # # model.add(SimpleRNN(32,return_sequences=True))
    # model.add(SimpleRNN(32,return_sequences=True))
    # model.add(SimpleRNN(32))
    # model.add(Dense(4, activation='softmax'))
    #
    # model.compile(loss='categorical_crossentropy', optimizer='adadelta', metrics=['accuracy'])

    if os.path.exists(cf.GENERAL_MODEL_NAME):
        model = load_model(cf.GENERAL_MODEL_NAME)

        return model
    else:
        return None