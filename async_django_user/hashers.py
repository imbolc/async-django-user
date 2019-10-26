import secrets
import hashlib
import importlib
import warnings
from .utils import get_random_string
import base64
import binascii


def pbkdf2(password, salt, iterations, dklen=0, digest=None):
    """Return the hash of password using pbkdf2."""
    if digest is None:
        digest = hashlib.sha256
    dklen = dklen or None
    password = password.encode("utf-8")
    salt = salt.encode("utf-8")
    return hashlib.pbkdf2_hmac(
        digest().name, password, salt, iterations, dklen
    )


def constant_time_compare(val1, val2):
    """Return True if the two strings are equal, False otherwise."""
    return secrets.compare_digest(val1, val2)


def mask_hash(hash, show=6, char="*"):
    """
    Return the given hash, with only the first ``show`` number shown. The
    rest are masked with ``char`` for security reasons.
    """
    masked = hash[:show]
    masked += char * len(hash[show:])
    return masked


class BasePasswordHasher:
    """
    Abstract base class for password hashers

    When creating your own hasher, you need to override algorithm,
    verify(), encode() and safe_summary().

    PasswordHasher objects are immutable.
    """

    algorithm = None
    library = None

    def _load_library(self):
        if self.library is not None:
            if isinstance(self.library, (tuple, list)):
                name, mod_path = self.library
            else:
                mod_path = self.library
            try:
                module = importlib.import_module(mod_path)
            except ImportError as e:
                raise ValueError(
                    "Couldn't load %r algorithm library: %s"
                    % (self.__class__.__name__, e)
                )
            return module
        raise ValueError(
            "Hasher %r doesn't specify a library attribute"
            % self.__class__.__name__
        )

    def salt(self):
        """Generate a cryptographically secure nonce salt in ASCII."""
        return get_random_string()

    def verify(self, password, encoded):
        """Check if the given password is correct."""
        raise NotImplementedError(
            "subclasses of BasePasswordHasher must provide a verify() method"
        )

    def encode(self, password, salt):
        """
        Create an encoded database value.

        The result is normally formatted as "algorithm$salt$hash" and
        must be fewer than 128 characters.
        """
        raise NotImplementedError(
            "subclasses of BasePasswordHasher must provide an encode() method"
        )

    def safe_summary(self, encoded):
        """
        Return a summary of safe values.

        The result is a dictionary and will be used where the password field
        must be displayed to construct a safe representation of the password.
        """
        raise NotImplementedError(
            "subclasses of BasePasswordHasher must provide a safe_summary() method"  # noqa
        )

    def must_update(self, encoded):
        return False

    def harden_runtime(self, password, encoded):
        """
        Bridge the runtime gap between the work factor supplied in `encoded`
        and the work factor suggested by this hasher.

        Taking PBKDF2 as an example, if `encoded` contains 20000 iterations and
        `self.iterations` is 30000, this method should run password through
        another 10000 iterations of PBKDF2. Similar approaches should exist
        for any hasher that has a work factor. If not, this method should be
        defined as a no-op to silence the warning.
        """
        warnings.warn(
            "subclasses of BasePasswordHasher should provide a harden_runtime() method"  # noqa
        )


class PBKDF2PasswordHasher(BasePasswordHasher):
    """
    Secure password hashing using the PBKDF2 algorithm (recommended)

    Configured to use PBKDF2 + HMAC + SHA256.
    The result is a 64 byte binary string.  Iterations may be changed
    safely but you must rename the algorithm if you change SHA256.
    """

    algorithm = "pbkdf2_sha256"
    iterations = 216000
    digest = hashlib.sha256

    def encode(self, password, salt, iterations=None):
        assert password is not None
        assert salt and "$" not in salt
        iterations = iterations or self.iterations
        hash = pbkdf2(password, salt, iterations, digest=self.digest)
        hash = base64.b64encode(hash).decode("ascii").strip()
        return "%s$%d$%s$%s" % (self.algorithm, iterations, salt, hash)

    def verify(self, password, encoded):
        algorithm, iterations, salt, hash = encoded.split("$", 3)
        assert algorithm == self.algorithm
        encoded_2 = self.encode(password, salt, int(iterations))
        return constant_time_compare(encoded, encoded_2)

    def safe_summary(self, encoded):
        algorithm, iterations, salt, hash = encoded.split("$", 3)
        assert algorithm == self.algorithm
        return {
            "algorithm": algorithm,
            "iterations": iterations,
            "salt": mask_hash(salt),
            "hash": mask_hash(hash),
        }

    def must_update(self, encoded):
        algorithm, iterations, salt, hash = encoded.split("$", 3)
        return int(iterations) != self.iterations

    def harden_runtime(self, password, encoded):
        algorithm, iterations, salt, hash = encoded.split("$", 3)
        extra_iterations = self.iterations - int(iterations)
        if extra_iterations > 0:
            self.encode(password, salt, extra_iterations)


class PBKDF2SHA1PasswordHasher(PBKDF2PasswordHasher):
    """
    Alternate PBKDF2 hasher which uses SHA1, the default PRF
    recommended by PKCS #5. This is compatible with other
    implementations of PBKDF2, such as openssl's
    PKCS5_PBKDF2_HMAC_SHA1().
    """

    algorithm = "pbkdf2_sha1"
    digest = hashlib.sha1


class Argon2PasswordHasher(BasePasswordHasher):
    """
    Secure password hashing using the argon2 algorithm.

    This is the winner of the Password Hashing Competition 2013-2015
    (https://password-hashing.net). It requires the argon2-cffi library which
    depends on native C code and might cause portability issues.
    """

    algorithm = "argon2"
    library = "argon2"

    time_cost = 2
    memory_cost = 512
    parallelism = 2

    def encode(self, password, salt):
        argon2 = self._load_library()
        data = argon2.low_level.hash_secret(
            password.encode(),
            salt.encode(),
            time_cost=self.time_cost,
            memory_cost=self.memory_cost,
            parallelism=self.parallelism,
            hash_len=argon2.DEFAULT_HASH_LENGTH,
            type=argon2.low_level.Type.I,
        )
        return self.algorithm + data.decode("ascii")

    def verify(self, password, encoded):
        argon2 = self._load_library()
        algorithm, rest = encoded.split("$", 1)
        assert algorithm == self.algorithm
        try:
            return argon2.low_level.verify_secret(
                ("$" + rest).encode("ascii"),
                password.encode(),
                type=argon2.low_level.Type.I,
            )
        except argon2.exceptions.VerificationError:
            return False

    def safe_summary(self, encoded):
        (
            algorithm,
            variety,
            version,
            time_cost,
            memory_cost,
            parallelism,
            salt,
            data,
        ) = self._decode(encoded)
        assert algorithm == self.algorithm
        return {
            "algorithm": algorithm,
            "variety": variety,
            "version": version,
            "memory cost": memory_cost,
            "time cost": time_cost,
            "parallelism": parallelism,
            "salt": mask_hash(salt),
            "hash": mask_hash(data),
        }

    def must_update(self, encoded):
        (
            algorithm,
            variety,
            version,
            time_cost,
            memory_cost,
            parallelism,
            salt,
            data,
        ) = self._decode(encoded)
        assert algorithm == self.algorithm
        argon2 = self._load_library()
        return (
            argon2.low_level.ARGON2_VERSION != version
            or self.time_cost != time_cost
            or self.memory_cost != memory_cost
            or self.parallelism != parallelism
        )

    def harden_runtime(self, password, encoded):
        # The runtime for Argon2 is too complicated to implement a sensible
        # hardening algorithm.
        pass

    def _decode(self, encoded):
        """
        Split an encoded hash and return: (
            algorithm, variety, version, time_cost, memory_cost,
            parallelism, salt, data,
        ).
        """
        bits = encoded.split("$")
        if len(bits) == 5:
            # Argon2 < 1.3
            algorithm, variety, raw_params, salt, data = bits
            version = 0x10
        else:
            assert len(bits) == 6
            algorithm, variety, raw_version, raw_params, salt, data = bits
            assert raw_version.startswith("v=")
            version = int(raw_version[len("v=") :])  # noqa
        params = dict(bit.split("=", 1) for bit in raw_params.split(","))
        assert len(params) == 3 and all(x in params for x in ("t", "m", "p"))
        time_cost = int(params["t"])
        memory_cost = int(params["m"])
        parallelism = int(params["p"])
        return (
            algorithm,
            variety,
            version,
            time_cost,
            memory_cost,
            parallelism,
            salt,
            data,
        )


class BCryptSHA256PasswordHasher(BasePasswordHasher):
    """
    Secure password hashing using the bcrypt algorithm (recommended)

    This is considered by many to be the most secure algorithm but you
    must first install the bcrypt library.  Please be warned that
    this library depends on native C code and might cause portability
    issues.
    """

    algorithm = "bcrypt_sha256"
    digest = hashlib.sha256
    library = ("bcrypt", "bcrypt")
    rounds = 12

    def salt(self):
        bcrypt = self._load_library()
        return bcrypt.gensalt(self.rounds)

    def encode(self, password, salt):
        bcrypt = self._load_library()
        password = password.encode()
        # Hash the password prior to using bcrypt to prevent password
        # truncation as described in #20138.
        if self.digest is not None:
            # Use binascii.hexlify() because a hex encoded bytestring is str.
            password = binascii.hexlify(self.digest(password).digest())

        data = bcrypt.hashpw(password, salt)
        return "%s$%s" % (self.algorithm, data.decode("ascii"))

    def verify(self, password, encoded):
        algorithm, data = encoded.split("$", 1)
        assert algorithm == self.algorithm
        encoded_2 = self.encode(password, data.encode("ascii"))
        return constant_time_compare(encoded, encoded_2)

    def safe_summary(self, encoded):
        algorithm, empty, algostr, work_factor, data = encoded.split("$", 4)
        assert algorithm == self.algorithm
        salt, checksum = data[:22], data[22:]
        return {
            "algorithm": algorithm,
            "work factor": work_factor,
            "salt": mask_hash(salt),
            "checksum": mask_hash(checksum),
        }

    def must_update(self, encoded):
        algorithm, empty, algostr, rounds, data = encoded.split("$", 4)
        return int(rounds) != self.rounds

    def harden_runtime(self, password, encoded):
        _, data = encoded.split("$", 1)
        salt = data[:29]  # Length of the salt in bcrypt.
        rounds = data.split("$")[2]
        # work factor is logarithmic, adding one doubles the load.
        diff = 2 ** (self.rounds - int(rounds)) - 1
        while diff > 0:
            self.encode(password, salt.encode("ascii"))
            diff -= 1


class BCryptPasswordHasher(BCryptSHA256PasswordHasher):
    """
    Secure password hashing using the bcrypt algorithm

    This is considered by many to be the most secure algorithm but you
    must first install the bcrypt library.  Please be warned that
    this library depends on native C code and might cause portability
    issues.

    This hasher does not first hash the password which means it is subject to
    bcrypt's 72 bytes password truncation. Most use cases should prefer the
    BCryptSHA256PasswordHasher.
    """

    algorithm = "bcrypt"
    digest = None


class SHA1PasswordHasher(BasePasswordHasher):
    """
    The SHA1 password hashing algorithm (not recommended)
    """

    algorithm = "sha1"

    def encode(self, password, salt):
        assert password is not None
        assert salt and "$" not in salt
        hash = hashlib.sha1((salt + password).encode()).hexdigest()
        return "%s$%s$%s" % (self.algorithm, salt, hash)

    def verify(self, password, encoded):
        algorithm, salt, hash = encoded.split("$", 2)
        assert algorithm == self.algorithm
        encoded_2 = self.encode(password, salt)
        return constant_time_compare(encoded, encoded_2)

    def safe_summary(self, encoded):
        algorithm, salt, hash = encoded.split("$", 2)
        assert algorithm == self.algorithm
        return {
            "algorithm": algorithm,
            "salt": mask_hash(salt, show=2),
            "hash": mask_hash(hash),
        }

    def harden_runtime(self, password, encoded):
        pass


class MD5PasswordHasher(BasePasswordHasher):
    """
    The Salted MD5 password hashing algorithm (not recommended)
    """

    algorithm = "md5"

    def encode(self, password, salt):
        assert password is not None
        assert salt and "$" not in salt
        hash = hashlib.md5((salt + password).encode()).hexdigest()
        return "%s$%s$%s" % (self.algorithm, salt, hash)

    def verify(self, password, encoded):
        algorithm, salt, hash = encoded.split("$", 2)
        assert algorithm == self.algorithm
        encoded_2 = self.encode(password, salt)
        return constant_time_compare(encoded, encoded_2)

    def safe_summary(self, encoded):
        algorithm, salt, hash = encoded.split("$", 2)
        assert algorithm == self.algorithm
        return {
            "algorithm": algorithm,
            "salt": mask_hash(salt, show=2),
            "hash": mask_hash(hash),
        }

    def harden_runtime(self, password, encoded):
        pass


class UnsaltedSHA1PasswordHasher(BasePasswordHasher):
    """
    Very insecure algorithm that you should *never* use; store SHA1 hashes
    with an empty salt.

    This class is implemented because Django used to accept such password
    hashes. Some older Django installs still have these values lingering
    around so we need to handle and upgrade them properly.
    """

    algorithm = "unsalted_sha1"

    def salt(self):
        return ""

    def encode(self, password, salt):
        assert salt == ""
        hash = hashlib.sha1(password.encode()).hexdigest()
        return "sha1$$%s" % hash

    def verify(self, password, encoded):
        encoded_2 = self.encode(password, "")
        return constant_time_compare(encoded, encoded_2)

    def safe_summary(self, encoded):
        assert encoded.startswith("sha1$$")
        hash = encoded[6:]
        return {"algorithm": self.algorithm, "hash": mask_hash(hash)}

    def harden_runtime(self, password, encoded):
        pass


class UnsaltedMD5PasswordHasher(BasePasswordHasher):
    """
    Incredibly insecure algorithm that you should *never* use; stores unsalted
    MD5 hashes without the algorithm prefix, also accepts MD5 hashes with an
    empty salt.

    This class is implemented because Django used to store passwords this way
    and to accept such password hashes. Some older Django installs still have
    these values lingering around so we need to handle and upgrade them
    properly.
    """

    algorithm = "unsalted_md5"

    def salt(self):
        return ""

    def encode(self, password, salt):
        assert salt == ""
        return hashlib.md5(password.encode()).hexdigest()

    def verify(self, password, encoded):
        if len(encoded) == 37 and encoded.startswith("md5$$"):
            encoded = encoded[5:]
        encoded_2 = self.encode(password, "")
        return constant_time_compare(encoded, encoded_2)

    def safe_summary(self, encoded):
        return {
            "algorithm": self.algorithm,
            "hash": mask_hash(encoded, show=3),
        }

    def harden_runtime(self, password, encoded):
        pass


class CryptPasswordHasher(BasePasswordHasher):
    """
    Password hashing using UNIX crypt (not recommended)

    The crypt module is not supported on all platforms.
    """

    algorithm = "crypt"
    library = "crypt"

    def salt(self):
        return get_random_string(2)

    def encode(self, password, salt):
        crypt = self._load_library()
        assert len(salt) == 2
        data = crypt.crypt(password, salt)
        assert (
            data is not None
        )  # A platform like OpenBSD with a dummy crypt module.
        # we don't need to store the salt, but Django used to do this
        return "%s$%s$%s" % (self.algorithm, "", data)

    def verify(self, password, encoded):
        crypt = self._load_library()
        algorithm, salt, data = encoded.split("$", 2)
        assert algorithm == self.algorithm
        return constant_time_compare(data, crypt.crypt(password, data))

    def safe_summary(self, encoded):
        algorithm, salt, data = encoded.split("$", 2)
        assert algorithm == self.algorithm
        return {
            "algorithm": algorithm,
            "salt": salt,
            "hash": mask_hash(data, show=3),
        }

    def harden_runtime(self, password, encoded):
        pass
